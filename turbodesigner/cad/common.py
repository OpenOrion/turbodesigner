from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, List, Optional
import cadquery as cq
import cq_warehouse.extensions as cq_warehouse_extensions
from cq_warehouse.fastener import SocketHeadCapScrew, HeatSetNut
import numpy as np
import re


@dataclass(frozen=True)
class HeatSetDims:
    size: str
    nut_diameter: float
    nut_thickness: float
    thread_diameter: float


@dataclass(frozen=True)
class ScrewDims:
    size: str
    head_diameter: float
    length: float


class CadColors:
    """Realistic material colors for turbomachinery CAD assemblies."""
    # Titanium alloy (Ti-6Al-4V) — blades
    BLADE = cq.Color(0.78, 0.76, 0.74)
    # Nickel superalloy (Inconel 718) — shaft/rotor disks
    SHAFT = cq.Color(0.65, 0.63, 0.60)
    # Aluminum alloy (6061-T6) — casing
    CASING = cq.Color(0.82, 0.84, 0.86)
    # Stainless steel — fasteners (screws, heatsets)
    FASTENER = cq.Color(0.55, 0.55, 0.55)


def colored_assembly(color: cq.Color) -> cq.Assembly:
    """Create a cq.Assembly that applies a color to all children after population.

    Use as baseAssembly for cq_warehouse fastener methods, then call
    colorize() before adding to the parent assembly.
    """
    asm = cq.Assembly()
    _original_add = asm.add

    def _colored_add(*args, **kwargs):
        kwargs.setdefault("color", color)
        return _original_add(*args, **kwargs)

    asm.add = _colored_add  # type: ignore[method-assign]
    return asm


class ExtendedWorkplane(cq.Workplane):
    clearanceHole = cq_warehouse_extensions._clearanceHole
    tapHole = cq_warehouse_extensions._tapHole
    threadedHole = cq_warehouse_extensions._threadedHole
    insertHole = cq_warehouse_extensions._insertHole
    pressFitHole = cq_warehouse_extensions._pressFitHole

    def ring(self, radius: float, thickness: float, depth: float) -> "ExtendedWorkplane":
        return (
            self
            .circle(radius)
            .circle(radius - thickness)
            .extrude(depth)
        )

    def truncated_cone(self, start_radius: float, end_radius: float, height: float):
        plane_world_coords = self.plane.toWorldCoords((0, 0, 0))
        path = cq.Workplane("XZ").moveTo(0, plane_world_coords.z).lineTo(0, height + plane_world_coords.z)

        return (
            self
            .circle(start_radius)
            .transformed(offset=cq.Vector(0, 0, height))
            .circle(end_radius)
            .sweep(path, multisection=True, makeSolid=True)
            .clean()
        )

    def hollow_truncated_cone(self, inner_start_radius: float, inner_end_radius: float, height: float, start_thickness: float, end_thickness: float):
        outer_radius = inner_start_radius + start_thickness
        return (
            self
            .truncated_cone(outer_radius, outer_radius, height)
            .cut(
                ExtendedWorkplane("XY")
                .truncated_cone(inner_start_radius, inner_end_radius, height)
            )
        )

    def mutatePoints(self, callback: Callable[[cq.Location], cq.Location]):
        for (i, loc) in enumerate(self.objects):
            if isinstance(loc, cq.Vertex) or isinstance(loc, cq.Vector):
                loc = cq.Location(self.plane, loc.toTuple())

            assert isinstance(loc, cq.Location)
            mutated_loc = callback(loc)
            self.objects[i] = mutated_loc

        return self
 

class FastenerPredicter:
    @staticmethod
    def get_nominal_size(
        target_diameter: float,
        nominal_size_range: List[str],
    ):
        for nominal_size in nominal_size_range:
            nominal_diameter = float(nominal_size.split("-")[0].replace("M", ""))
            if target_diameter <= nominal_diameter:
                return nominal_size

        raise ValueError(f"nominal size for target diameter {target_diameter} could not be found")

    @staticmethod
    def get_nominal_length(
        target_length: float,
        nominal_length_range: List[float],
    ):
        for nominal_length in nominal_length_range:
            if target_length <= nominal_length:
                return nominal_length
        raise ValueError(f"nominal length for target length {target_length} could not be found")

    @staticmethod
    def _get_heatset_dims(size: str, type: str):
        """Get heatset dimensions from raw data without constructing 3D geometry."""
        data = HeatSetNut.fastener_data
        prefix = f"{type}:"
        s_val = float(data[size][f"{prefix}s"])
        m_val = float(data[size][f"{prefix}m"])
        thread_diameter = float(size.split("-")[0].replace("M", ""))
        return s_val, m_val, thread_diameter  # nut_diameter, nut_thickness, thread_diameter

    @staticmethod
    def _get_screw_head_diameter(size: str, type: str):
        """Get screw head diameter from raw data without constructing 3D geometry."""
        data = SocketHeadCapScrew.fastener_data
        return float(data[size][f"{type}:dk "])

    @staticmethod
    def predict_heatset_dims(target_diameter: float, max_thickness: Optional[float] = None, type: str = "Hilitchi") -> HeatSetDims:
        """Predict heatset and return HeatSetDims without constructing 3D objects."""
        nominal_size_range = HeatSetNut.sizes(type)
        last_acceptable: Optional[HeatSetDims] = None
        for nominal_size in nominal_size_range:
            nut_diameter, nut_thickness, thread_diameter = FastenerPredicter._get_heatset_dims(nominal_size, type)
            dims = HeatSetDims(size=nominal_size, nut_diameter=nut_diameter, nut_thickness=nut_thickness, thread_diameter=thread_diameter)
            if max_thickness and nut_thickness <= max_thickness:
                last_acceptable = dims
            if target_diameter <= nut_diameter:
                if max_thickness and nut_thickness > max_thickness:
                    assert last_acceptable is not None, f"no heatsets are valid for max height {max_thickness}, closest heatset nut_diameter={nut_diameter}"
                    return last_acceptable
                return dims
        raise ValueError(f"nominal size for target diameter {target_diameter} could not be found")

    @staticmethod
    def predict_screw_dims(target_diameter: float, target_length: Optional[float] = None, type: str = "iso4762") -> ScrewDims:
        """Predict screw and return ScrewDims without constructing 3D objects."""
        nominal_length_range = SocketHeadCapScrew.nominal_length_range[type]
        predicted_length = nominal_length_range[0]
        if target_length:
            predicted_length = FastenerPredicter.get_nominal_length(target_length, nominal_length_range)

        nominal_size_range = SocketHeadCapScrew.sizes(type)
        predicted_size = FastenerPredicter.get_nominal_size(target_diameter, nominal_size_range)
        head_diameter = FastenerPredicter._get_screw_head_diameter(predicted_size, type)

        return ScrewDims(size=predicted_size, head_diameter=head_diameter, length=predicted_length)

    @staticmethod
    @lru_cache(maxsize=64)
    def predict_heatset(target_diameter: float, max_thickness: Optional[float] = None, type: str = "McMaster-Carr"):
        result = FastenerPredicter._search_heatset_type(target_diameter, max_thickness, type)
        if result is not None:
            return result
        # Search all other types
        for other_type in HeatSetNut.types():
            if other_type == type:
                continue
            result = FastenerPredicter._search_heatset_type(target_diameter, max_thickness, other_type)
            if result is not None:
                return result
        # Final fallback: return smallest diameter match from preferred type ignoring thickness
        result = FastenerPredicter._search_heatset_type(target_diameter, None, type)
        if result is not None:
            return result
        raise ValueError(f"nominal size for target diameter {target_diameter} could not be found")

    @staticmethod
    def _search_heatset_type(target_diameter: float, max_thickness: Optional[float], type: str) -> Optional[HeatSetNut]:
        try:
            nominal_size_range = HeatSetNut.sizes(type)
        except Exception:
            return None
        last_acceptable_height_heatset: Optional[HeatSetNut] = None
        first_diameter_match: Optional[HeatSetNut] = None
        for nominal_size in nominal_size_range:
            try:
                heatset = HeatSetNut(size=nominal_size, fastener_type=type, simple=True)
            except Exception:
                continue
            if max_thickness and heatset.nut_thickness <= max_thickness:
                last_acceptable_height_heatset = heatset
            if target_diameter <= heatset.nut_diameter:
                if first_diameter_match is None:
                    first_diameter_match = heatset
                if not max_thickness or heatset.nut_thickness <= max_thickness:
                    return heatset
                if last_acceptable_height_heatset is not None:
                    return last_acceptable_height_heatset
        return None

    @staticmethod
    @lru_cache(maxsize=64)
    def predict_screw(target_diameter: float, target_length: Optional[float] = None, type: str = "iso4762"):
        nominal_length_range = SocketHeadCapScrew.nominal_length_range[type]
        predicted_length = nominal_length_range[0]
        if target_length:
            predicted_length = FastenerPredicter.get_nominal_length(target_length, nominal_length_range)
        
        nominal_size_range = SocketHeadCapScrew.sizes(type)
        predicted_size = FastenerPredicter.get_nominal_size(target_diameter, nominal_size_range)

        return SocketHeadCapScrew(predicted_size, predicted_length, type)
