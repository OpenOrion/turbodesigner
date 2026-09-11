"""
Parametric annular combustor CAD generator.

This module intentionally does not integrate with the TurboDesigner CLI.
It provides a reusable API that can later be connected to the CLI,
reports, or other design tools.

The generator takes an existing TurboDesigner ``Turbomachinery`` object
and a ``CombustorParameters`` object, then returns a CadQuery Workplane.

TurboDesigner uses SI units internally:
    length       -> m
    pressure     -> Pa
    temperature  -> K
    mass flow    -> kg/s
    velocity     -> m/s

CadQuery geometry is constructed in millimeters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cadquery as cq

from turbodesigner.units import MM
from turbodesigner.turbomachinery import Turbomachinery


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------


@dataclass
class CombustorParameters:
    """
    Parameters controlling the combustor geometry.

    All length parameters are in meters so that the interface is consistent
    with the rest of TurboDesigner.

    The compressor/turbomachinery conditions are NOT duplicated here.
    They are obtained from the Turbomachinery object passed to
    ``generate_combustor()``.
    """

    # ------------------------------------------------------------------
    # Overall combustor
    # ------------------------------------------------------------------

    length: float = 0.20

    # Radial clearance between the compressor annulus and combustor casing.
    radial_clearance: float = 0.010

    # ------------------------------------------------------------------
    # Liner
    # ------------------------------------------------------------------

    liner_thickness: float = 0.002

    # Radial distance from casing to liner.
    casing_clearance: float = 0.010

    # ------------------------------------------------------------------
    # Combustion zones
    #
    # These are fractions of the total combustor length.
    # ------------------------------------------------------------------

    primary_zone_fraction: float = 0.30
    secondary_zone_fraction: float = 0.30
    dilution_zone_fraction: float = 0.40

    # ------------------------------------------------------------------
    # Primary holes
    # ------------------------------------------------------------------

    primary_hole_diameter: float = 0.004
    primary_hole_count: int = 24

    # Position of the primary-hole row as a fraction of combustor length.
    primary_hole_position: float = 0.15

    # ------------------------------------------------------------------
    # Secondary holes
    # ------------------------------------------------------------------

    secondary_hole_diameter: float = 0.006
    secondary_hole_count: int = 18

    secondary_hole_position: float = 0.50

    # ------------------------------------------------------------------
    # Dilution holes
    # ------------------------------------------------------------------

    dilution_hole_diameter: float = 0.008
    dilution_hole_count: int = 12

    dilution_hole_position: float = 0.80

    # ------------------------------------------------------------------
    # Optional combustor dome
    # ------------------------------------------------------------------

    dome_length: float = 0.020
    dome_thickness: float = 0.002

    # Whether to generate the dome.
    include_dome: bool = True

    def validate(self) -> None:
        """Validate combustor parameters."""

        if self.length <= 0:
            raise ValueError("Combustor length must be greater than zero.")

        if self.radial_clearance < 0:
            raise ValueError("Radial clearance cannot be negative.")

        if self.liner_thickness <= 0:
            raise ValueError("Liner thickness must be greater than zero.")

        if self.casing_clearance < 0:
            raise ValueError("Casing clearance cannot be negative.")

        if self.dome_length < 0:
            raise ValueError("Dome length cannot be negative.")

        if self.dome_thickness < 0:
            raise ValueError("Dome thickness cannot be negative.")

        # Zone fractions should describe the complete combustor.
        zone_sum = (
            self.primary_zone_fraction
            + self.secondary_zone_fraction
            + self.dilution_zone_fraction
        )

        if abs(zone_sum - 1.0) > 1e-9:
            raise ValueError(
                "primary_zone_fraction + secondary_zone_fraction + "
                "dilution_zone_fraction must equal 1.0."
            )

        for name, value in (
            ("primary_zone_fraction", self.primary_zone_fraction),
            ("secondary_zone_fraction", self.secondary_zone_fraction),
            ("dilution_zone_fraction", self.dilution_zone_fraction),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero.")

        # Hole parameters.
        if self.primary_hole_diameter <= 0:
            raise ValueError("Primary hole diameter must be greater than zero.")

        if self.secondary_hole_diameter <= 0:
            raise ValueError("Secondary hole diameter must be greater than zero.")

        if self.dilution_hole_diameter <= 0:
            raise ValueError("Dilution hole diameter must be greater than zero.")

        if self.primary_hole_count <= 0:
            raise ValueError("Primary hole count must be greater than zero.")

        if self.secondary_hole_count <= 0:
            raise ValueError("Secondary hole count must be greater than zero.")

        if self.dilution_hole_count <= 0:
            raise ValueError("Dilution hole count must be greater than zero.")

        for name, value in (
            ("primary_hole_position", self.primary_hole_position),
            ("secondary_hole_position", self.secondary_hole_position),
            ("dilution_hole_position", self.dilution_hole_position),
        ):
            if not 0.0 < value < 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1."
                )


# ---------------------------------------------------------------------------
# Derived geometry
# ---------------------------------------------------------------------------


@dataclass
class CombustorGeometry:
    """
    Derived combustor geometry in meters.

    This is kept separate from CombustorParameters so that the geometry
    calculation can be inspected independently from the CAD construction.
    """

    inlet_inner_radius: float
    inlet_outer_radius: float

    casing_inner_radius: float
    casing_outer_radius: float

    liner_inner_radius: float
    liner_outer_radius: float

    length: float

    dome_length: float

    @property
    def inlet_annulus_height(self) -> float:
        return self.inlet_outer_radius - self.inlet_inner_radius

    @property
    def liner_annulus_height(self) -> float:
        return self.liner_outer_radius - self.liner_inner_radius


# ---------------------------------------------------------------------------
# Geometry calculation
# ---------------------------------------------------------------------------


def calculate_combustor_geometry(
    turbomachinery: Turbomachinery,
    parameters: CombustorParameters,
) -> CombustorGeometry:
    """
    Calculate combustor dimensions from the TurboDesigner machine.

    The compressor inlet annulus is used as the starting point.

    Parameters
    ----------
    turbomachinery:
        Existing TurboDesigner Turbomachinery object.

    parameters:
        Combustor-specific design parameters.

    Returns
    -------
    CombustorGeometry
        Derived dimensions in meters.
    """

    parameters.validate()

    # TurboDesigner already calculates these in meters.
    inlet_hub_radius = turbomachinery.inlet_hub_radius
    inlet_tip_radius = turbomachinery.inlet_tip_radius

    if inlet_hub_radius <= 0:
        raise ValueError("TurboDesigner returned an invalid hub radius.")

    if inlet_tip_radius <= inlet_hub_radius:
        raise ValueError(
            "TurboDesigner returned an invalid inlet annulus."
        )

    # Start with the compressor tip radius and add clearance outward.
    casing_inner_radius = (
        inlet_tip_radius + parameters.radial_clearance
    )

    # The casing is deliberately made somewhat thicker than the liner.
    casing_thickness = max(
        parameters.liner_thickness * 3.0,
        0.003,
    )

    casing_outer_radius = casing_inner_radius + casing_thickness

    # The inner liner follows the compressor hub radius.
    liner_inner_radius = max(
        inlet_hub_radius - parameters.radial_clearance,
        inlet_hub_radius * 0.50,
    )

    # The outer liner is separated from the casing by a cooling/air gap.
    liner_outer_radius = (
        casing_inner_radius - parameters.casing_clearance
    )

    if liner_outer_radius <= liner_inner_radius:
        raise ValueError(
            "Calculated liner does not fit inside the combustor casing. "
            "Reduce casing_clearance/radial_clearance or increase the "
            "available annulus."
        )

    return CombustorGeometry(
        inlet_inner_radius= inlet_hub_radius,
        inlet_outer_radius=inlet_tip_radius,
        casing_inner_radius=casing_inner_radius,
        casing_outer_radius=casing_outer_radius,
        liner_inner_radius=liner_inner_radius,
        liner_outer_radius=liner_outer_radius,
        length=parameters.length,
        dome_length=parameters.dome_length,
    )


# ---------------------------------------------------------------------------
# CadQuery helpers
# ---------------------------------------------------------------------------


def _annular_cylinder(
    inner_radius_m: float,
    outer_radius_m: float,
    length_m: float,
) -> cq.Workplane:
    """
    Create an annular cylinder.

    The cylinder axis is the X axis.

    CadQuery's normal extrusion direction is Z, so the finished geometry
    is rotated so that:
        X = combustor axial direction
        Y/Z = radial directions
    """

    inner_radius_mm = inner_radius_m * MM
    outer_radius_mm = outer_radius_m * MM
    length_mm = length_m * MM

    model = (
        cq.Workplane("XY")
        .circle(outer_radius_mm)
        .circle(inner_radius_mm)
        .extrude(length_mm)
    )

    # Z -> X
    model = model.rotate(
        (0, 0, 0),
        (0, 1, 0),
        90,
    )

    return model


def _cylinder_x(
    radius_m: float,
    length_m: float,
    x_start_m: float = 0.0,
) -> cq.Workplane:
    """
    Create a cylinder whose axis is the X axis.
    """

    radius_mm = radius_m * MM
    length_mm = length_m * MM
    x_start_mm = x_start_m * MM

    model = (
        cq.Workplane("YZ")
        .circle(radius_mm)
        .extrude(length_mm)
    )

    if x_start_mm != 0:
        model = model.translate(
            (x_start_mm, 0, 0)
        )

    return model


def _radial_hole(
    radius_m: float,
    diameter_m: float,
    angle_deg: float,
    axial_position_m: float,
    depth_m: float,
) -> cq.Workplane:
    """
    Create one radial cylindrical hole cutter.

    The cutter starts outside the liner/casing and travels radially inward.

    Coordinates:
        X = axial direction
        Y/Z = radial plane
    """

    radius_mm = radius_m * MM
    diameter_mm = diameter_m * MM
    axial_mm = axial_position_m * MM
    depth_mm = depth_m * MM

    # Start with a cylinder along Z.
    hole = (
        cq.Workplane("XY")
        .circle(diameter_mm / 2.0)
        .extrude(depth_mm)
    )

    # Move the cylinder's base to the outer radial surface.
    hole = hole.translate(
        (axial_mm, radius_mm, 0)
    )

    # Z axis -> radial direction in the YZ plane.
    hole = hole.rotate(
        (axial_mm, radius_mm, 0),
        (axial_mm, radius_mm, 1),
        90,
    )

    # Rotate around the combustor axis.
    hole = hole.rotate(
        (0, 0, 0),
        (1, 0, 0),
        angle_deg,
    )

    return hole


def _hole_row(
    model: cq.Workplane,
    outer_radius_m: float,
    diameter_m: float,
    count: int,
    axial_position_m: float,
    depth_m: float,
) -> cq.Workplane:
    """
    Cut one complete circumferential row of radial holes.
    """

    if count <= 0:
        return model

    result = model

    for index in range(count):
        angle = 360.0 * index / count

        cutter = _radial_hole(
            radius_m=outer_radius_m,
            diameter_m=diameter_m,
            angle_deg=angle,
            axial_position_m=axial_position_m,
            depth_m=depth_m,
        )

        result = result.cut(cutter)

    return result


# ---------------------------------------------------------------------------
# Dome
# ---------------------------------------------------------------------------


def _make_dome(
    geometry: CombustorGeometry,
    parameters: CombustorParameters,
) -> cq.Workplane:
    """
    Create a simple annular combustor dome.

    This is intentionally a simple parametric starting geometry rather than
    a detailed swirler/dome design.
    """

    if not parameters.include_dome:
        return cq.Workplane("XY")

    dome_length = parameters.dome_length

    if dome_length <= 0:
        return cq.Workplane("XY")

    dome_inner_radius = geometry.liner_inner_radius
    dome_outer_radius = geometry.liner_outer_radius

    dome = _annular_cylinder(
        inner_radius_m=dome_inner_radius,
        outer_radius_m=dome_outer_radius,
        length_m=dome_length,
    )

    return dome


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------


def generate_combustor(
    turbomachinery: Turbomachinery,
    parameters: Optional[CombustorParameters] = None,
) -> cq.Workplane:
    """
    Generate a parametric annular combustor.

    Parameters
    ----------
    turbomachinery:
        A fully calculated TurboDesigner Turbomachinery object.

    parameters:
        Combustor-specific geometry parameters.

        If omitted, default CombustorParameters are used.

    Returns
    -------
    cq.Workplane
        CadQuery model containing the combustor geometry.

    Notes
    -----
    The generated geometry is a CAD starting point. It is not intended to
    claim that the resulting combustor is thermodynamically, structurally,
    thermally, or aerodynamically validated.
    """

    if parameters is None:
        parameters = CombustorParameters()

    parameters.validate()

    geometry = calculate_combustor_geometry(
        turbomachinery,
        parameters,
    )

    # ------------------------------------------------------------------
    # 1. Outer casing
    # ------------------------------------------------------------------

    casing = _annular_cylinder(
        inner_radius_m=geometry.casing_inner_radius,
        outer_radius_m=geometry.casing_outer_radius,
        length_m=geometry.length,
    )

    # ------------------------------------------------------------------
    # 2. Inner liner
    # ------------------------------------------------------------------

    inner_liner = _annular_cylinder(
        inner_radius_m=geometry.liner_inner_radius,
        outer_radius_m=geometry.liner_outer_radius,
        length_m=geometry.length,
    )

    # ------------------------------------------------------------------
    # 3. Cut holes through the outer liner surface.
    #
    # The cutter is made deep enough to pass completely through the
    # liner and enter the surrounding annulus.
    # ------------------------------------------------------------------

    hole_depth = (
        geometry.liner_outer_radius
        - geometry.liner_inner_radius
        + parameters.liner_thickness * 2.0
    )

    # Primary-zone holes.
    primary_x = (
        parameters.length
        * parameters.primary_hole_position
    )

    inner_liner = _hole_row(
        model=inner_liner,
        outer_radius_m=geometry.liner_outer_radius,
        diameter_m=parameters.primary_hole_diameter,
        count=parameters.primary_hole_count,
        axial_position_m=primary_x,
        depth_m=hole_depth,
    )

    # Secondary-zone holes.
    secondary_x = (
        parameters.length
        * parameters.secondary_hole_position
    )

    inner_liner = _hole_row(
        model=inner_liner,
        outer_radius_m=geometry.liner_outer_radius,
        diameter_m=parameters.secondary_hole_diameter,
        count=parameters.secondary_hole_count,
        axial_position_m=secondary_x,
        depth_m=hole_depth,
    )

    # Dilution-zone holes.
    dilution_x = (
        parameters.length
        * parameters.dilution_hole_position
    )

    inner_liner = _hole_row(
        model=inner_liner,
        outer_radius_m=geometry.liner_outer_radius,
        diameter_m=parameters.dilution_hole_diameter,
        count=parameters.dilution_hole_count,
        axial_position_m=dilution_x,
        depth_m=hole_depth,
    )

    # ------------------------------------------------------------------
    # 4. Dome
    # ------------------------------------------------------------------

    dome = _make_dome(
        geometry,
        parameters,
    )

    # ------------------------------------------------------------------
    # 5. Combine the components.
    #
    # The result is a single CadQuery Workplane containing:
    #
    #   - outer casing
    #   - annular liner
    #   - combustor dome
    #
    # The holes have already been cut into the liner.
    # ------------------------------------------------------------------

    result = casing.union(inner_liner)

    if parameters.include_dome:
        result = result.union(dome)

    return result


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def combustor_summary(
    turbomachinery: Turbomachinery,
    parameters: CombustorParameters,
) -> dict:
    """
    Return useful calculated information about the combustor.

    This does not generate CAD.

    The returned dictionary can later be used by reports, the CLI,
    visualization code, or other TurboDesigner modules.
    """

    geometry = calculate_combustor_geometry(
        turbomachinery,
        parameters,
    )

    return {
        "mass_flow_rate_kg_s": turbomachinery.mass_flow_rate,
        "outlet_total_pressure_pa": turbomachinery.outlet_total_pressure,
        "outlet_total_temperature_k": turbomachinery.outlet_total_temperature,

        "compressor_inlet_hub_radius_m":
            turbomachinery.inlet_hub_radius,

        "compressor_inlet_tip_radius_m":
            turbomachinery.inlet_tip_radius,

        "compressor_inlet_mean_radius_m":
            turbomachinery.inlet_mean_radius,

        "compressor_inlet_mach":
            turbomachinery.inlet_mach_number,

        "combustor_length_m":
            geometry.length,

        "casing_inner_radius_m":
            geometry.casing_inner_radius,

        "casing_outer_radius_m":
            geometry.casing_outer_radius,

        "liner_inner_radius_m":
            geometry.liner_inner_radius,

        "liner_outer_radius_m":
            geometry.liner_outer_radius,

        "liner_annulus_height_m":
            geometry.liner_annulus_height,

        "primary_hole_diameter_m":
            parameters.primary_hole_diameter,

        "primary_hole_count":
            parameters.primary_hole_count,

        "secondary_hole_diameter_m":
            parameters.secondary_hole_diameter,

        "secondary_hole_count":
            parameters.secondary_hole_count,

        "dilution_hole_diameter_m":
            parameters.dilution_hole_diameter,

        "dilution_hole_count":
            parameters.dilution_hole_count,
    }


# ---------------------------------------------------------------------------
# Simple standalone test
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    """
    Basic development test.

    This section is NOT part of the TurboDesigner CLI.

    It simply loads a TurboDesigner design and displays the generated
    combustor when this file is executed directly.
    """

    from turbodesigner.cli.state import TurboDesign

    # Change this to your exported TurboDesigner design.
    DESIGN_FILE = "design.json"

    design = TurboDesign.from_file(DESIGN_FILE)
    tm = design.definition

    parameters = CombustorParameters(
        length=0.20,

        radial_clearance=0.010,

        liner_thickness=0.002,
        casing_clearance=0.010,

        primary_zone_fraction=0.30,
        secondary_zone_fraction=0.30,
        dilution_zone_fraction=0.40,

        primary_hole_diameter=0.004,
        primary_hole_count=24,
        primary_hole_position=0.15,

        secondary_hole_diameter=0.006,
        secondary_hole_count=18,
        secondary_hole_position=0.50,

        dilution_hole_diameter=0.008,
        dilution_hole_count=12,
        dilution_hole_position=0.80,

        dome_length=0.020,
        dome_thickness=0.002,

        include_dome=True,
    )

    print("\nTurboDesigner conditions:")
    print(f"  Mass flow:       {tm.mass_flow_rate:.3f} kg/s")
    print(f"  Outlet pressure: {tm.outlet_total_pressure:.1f} Pa")
    print(f"  Outlet temp:     {tm.outlet_total_temperature:.2f} K")
    print(f"  Inlet hub:       {tm.inlet_hub_radius:.6f} m")
    print(f"  Inlet tip:       {tm.inlet_tip_radius:.6f} m")
    print(f"  Inlet Mach:      {tm.inlet_mach_number:.4f}")

    geometry = calculate_combustor_geometry(
        tm,
        parameters,
    )

    print("\nCombustor geometry:")
    print(f"  Length:          {geometry.length:.4f} m")
    print(f"  Casing ID:       {geometry.casing_inner_radius * 2:.4f} m")
    print(f"  Casing OD:       {geometry.casing_outer_radius * 2:.4f} m")
    print(f"  Liner ID:        {geometry.liner_inner_radius * 2:.4f} m")
    print(f"  Liner OD:        {geometry.liner_outer_radius * 2:.4f} m")

    print("\nGenerating CAD...")

    model = generate_combustor(
        turbomachinery=tm,
        parameters=parameters,
    )

    print("Combustor generated successfully.")

    try:
        from cadquery.vis import show_object

        

    except ImportError:
        print(
            "\nCadQuery viewer is not available in this environment."
        )
        print(
            "The model was still generated successfully."
        )