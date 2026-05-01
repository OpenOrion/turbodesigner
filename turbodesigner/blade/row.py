from functools import cached_property
from typing import Literal, Optional
import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field
from turbodesigner.airfoils import AirfoilType, DCAAirfoil
from turbodesigner.blade.metal_angle_methods.johnsen_bullock import JohnsenBullockMetalAngleMethod
from turbodesigner.blade.metal_angles import MetalAngles
from turbodesigner.blade.vortex.common import Vortex
from turbodesigner.flow_station import FlowStation
from turbodesigner.attachments.firetree import FirtreeAttachment
from turbodesigner.units import MM

MetalAngleMethods = Literal["EqualsFlowAngles", "JohnsenBullock"]


class BladeRowCadExport(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    stage_number: int = Field(description="Stage number")
    disk_height: float = Field(description="Disk height (mm)")
    hub_radius: float = Field(description="Hub radius (mm)")
    tip_radius: float = Field(description="Tip radius (mm)")
    radii: npt.NDArray[np.float64] = Field(description="Blade station radii (mm)")
    airfoils: np.ndarray = Field(description="Airfoil coordinates for each blade radius (mm)")
    attachment: np.ndarray = Field(description="Attachment coordinates (mm)")
    attachment_with_tolerance: np.ndarray = Field(description="Attachment coordinates with tolerance (mm)")
    attachment_height: float = Field(description="Attachment height (mm)")
    attachment_bottom_width: float = Field(description="Attachment bottom width (mm)")
    number_of_blades: int = Field(description="Number of blades")
    twist_angle: float = Field(description="Twist angle of blade (deg)")
    is_rotating: bool = Field(description="Whether blade is rotating")


class BladeRow(BaseModel):
    """Calculates turbomachinery blade row."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=False)

    stage_number: int = Field(description="Stage number")

    stage_flow_station: FlowStation = Field(description="Stage flow station", exclude=True)

    vortex: Vortex = Field(description="Vortex distribution", exclude=True)

    aspect_ratio: float = Field(description="Aspect ratio (dimensionless)")

    spacing_to_chord: float = Field(description="Spacing to chord ratio (dimensionless)")

    max_thickness_to_chord: float = Field(description="Max thickness to chord (dimensionless)")

    is_rotating: bool = Field(description="Whether blade is rotating")

    num_streams: int = Field(description="Number of streams per blade (dimensionless)")

    metal_angle_method: MetalAngleMethods = Field(description="Metal angle method")

    next_stage_flow_station: Optional[FlowStation] = Field(default=None, description="Next stage flow station", exclude=True)

    deviation_iterations: int = Field(default=20, description="Nominal deviation iterations")

    def model_post_init(self, __context):
        assert self.num_streams % 2 != 0, "num_streams must be an odd number"
        if self.is_rotating and self.next_stage_flow_station is None:
            self.next_stage_flow_station = self.stage_flow_station.copy_stream(
                flow_angle=self.vortex.alpha(self.radii, is_rotating=False),
                radius=self.radii,
            )

    @cached_property
    def tip_radius(self) -> float:
        """Blade tip radius (m)"""
        rt = self.stage_flow_station.outer_radius
        assert isinstance(rt, float)
        return rt

    @cached_property
    def hub_radius(self) -> float:
        """Blade hub radius (m)"""
        rh = self.stage_flow_station.inner_radius
        assert isinstance(rh, float)
        return rh

    @cached_property
    def mean_radius(self) -> float:
        """Blade mean radius (m)"""
        rm = self.stage_flow_station.radius
        assert isinstance(rm, float)
        return rm

    @cached_property
    def height(self) -> float:
        """Blade height (m)"""
        return float(self.tip_radius - self.hub_radius)

    @cached_property
    def disk_height(self) -> float:
        """Disk height of blade row (m)"""
        xi = self.metal_angles.stagger_angle[0] if self.is_rotating else self.metal_angles.stagger_angle[-1]
        return float(np.abs(self.chord * np.cos(xi) * 1.25))

    @cached_property
    def chord(self) -> float:
        """Chord length (m)"""
        return float(self.height / self.aspect_ratio)

    @cached_property
    def max_thickness(self) -> float:
        """Max blade thickness (m)"""
        return float(self.max_thickness_to_chord * self.chord)

    @cached_property
    def num_blades(self) -> int:
        """Number of blades (dimensionless)"""
        Z = np.ceil(2 * np.pi * self.mean_radius / (self.spacing_to_chord * self.chord))
        if not self.is_rotating and not Z % 2 == 0:
            Z -= 1
        return int(Z)

    @cached_property
    def spacing(self) -> float:
        """Blade spacing (m)"""
        return float(2 * np.pi * self.hub_radius / self.num_blades)

    @cached_property
    def spacing_to_height(self) -> float:
        """Spacing to height ratio (dimensionless)"""
        return float(self.spacing / self.height)

    @cached_property
    def solidity(self) -> float:
        """Solidity (dimensionless)"""
        return float(1 / self.spacing_to_chord)

    @cached_property
    def de_haller(self):
        """De Haller number (dimensionless)"""
        if self.is_rotating:
            return self.next_flow_station.relative_velocity / self.flow_station.relative_velocity
        return self.next_flow_station.absolute_velocity / self.flow_station.absolute_velocity

    @cached_property
    def reynolds_number(self) -> float:
        """Reynolds number (dimensionless)"""
        return float(self.stage_flow_station.density * self.stage_flow_station.meridional_velocity * (self.chord / self.stage_flow_station.dynamic_viscosity))

    @cached_property
    def airfoil_type(self):
        # TODO: only have support of DCA airfoil generation at the moment
        return AirfoilType.DCA

    @cached_property
    def metal_angles(self) -> MetalAngles:
        if self.metal_angle_method == "JohnsenBullock":
            method = JohnsenBullockMetalAngleMethod(
                inlet_flow_angle=self.inlet_flow_angle,
                outlet_flow_angle=self.outlet_flow_angle,
                solidity=self.solidity,
                max_thickness_to_chord=self.max_thickness_to_chord,
                airfoil_type=self.airfoil_type,
            )
            offset = method.get_metal_angle_offset(self.deviation_iterations)
            return MetalAngles(
                inlet_flow_angle=self.inlet_flow_angle,
                outlet_flow_angle=self.outlet_flow_angle,
                incidence=offset.i,
                deviation=offset.delta,
            )
        return MetalAngles(
            inlet_flow_angle=self.inlet_flow_angle,
            outlet_flow_angle=self.outlet_flow_angle,
            incidence=0,
            deviation=0,
        )

    @cached_property
    def radii(self):
        """Blade radii (m)"""
        return np.linspace(self.hub_radius, self.tip_radius, self.num_streams, endpoint=True)

    @cached_property
    def flow_station(self) -> FlowStation:
        """Flow station at this blade row (FlowStation)"""
        return self.stage_flow_station.copy_stream(
            flow_angle=self.vortex.alpha(self.radii, self.is_rotating),
            radius=self.radii,
        )

    @cached_property
    def next_flow_station(self) -> FlowStation:
        """Exit flow station for this blade row (FlowStation)"""
        assert self.next_stage_flow_station is not None
        return self.next_stage_flow_station.copy_stream(
            flow_angle=self.vortex.alpha(self.radii, not self.is_rotating),
            radius=self.radii,
        )

    @cached_property
    def inlet_flow_angle(self):
        """Blade inlet flow angle (rad)"""
        if self.is_rotating:
            return self.flow_station.relative_flow_angle
        return self.flow_station.flow_angle

    @cached_property
    def outlet_flow_angle(self):
        """Blade outlet flow angle (rad)"""
        if self.is_rotating:
            assert self.next_stage_flow_station is not None
            return self.next_stage_flow_station.relative_flow_angle
        assert self.next_stage_flow_station is not None or self.vortex.mean_reaction == 0.5, "next_flow_station needs to be defined or Rc=0.5"
        if self.next_stage_flow_station is not None:
            return self.next_stage_flow_station.flow_angle
        return self.vortex.alpha(self.radii, is_rotating=not self.is_rotating)

    @cached_property
    def diffusion_factor(self):
        """Diffusion factor (dimensionless)"""
        return 1 - (np.cos(self.inlet_flow_angle) / np.cos(self.outlet_flow_angle)) + (np.cos(self.inlet_flow_angle) / 2) * self.solidity * (np.tan(self.inlet_flow_angle) - np.tan(self.outlet_flow_angle))

    @cached_property
    def airfoils(self):
        r0 = self.max_thickness * 0.15
        return [
            DCAAirfoil(self.chord, self.metal_angles.camber_angle[i], r0, self.max_thickness, self.metal_angles.stagger_angle[i])
            for i in range(self.num_streams)
        ]

    @cached_property
    def attachment(self) -> FirtreeAttachment:
        max_length = 0.75 * self.spacing if self.is_rotating else 1 * self.spacing
        return FirtreeAttachment(
            gamma=np.radians(40),
            beta=np.radians(40),
            ll=0.15 * self.spacing,
            lu=0.2 * self.spacing,
            Ri=0.05 * self.spacing,
            Ro=0.025 * self.spacing,
            R_dove=0.05 * self.spacing,
            max_length=max_length,
            num_stages=2,
            disk_radius=self.hub_radius,
            tolerance=0.0006,
            include_top_arc=self.is_rotating,
        )

    def to_cad_export(self) -> BladeRowCadExport:
        return BladeRowCadExport(
            stage_number=self.stage_number,
            disk_height=self.disk_height * MM,
            hub_radius=self.hub_radius * MM,
            tip_radius=self.tip_radius * MM,
            radii=self.radii * MM,
            airfoils=np.array([airfoil.get_coords() for airfoil in self.airfoils]) * MM,
            attachment=self.attachment.coords * MM,
            attachment_with_tolerance=self.attachment.coords_with_tolerance * MM,
            attachment_height=self.attachment.height * MM,
            attachment_bottom_width=self.attachment.bottom_width * MM,
            number_of_blades=self.num_blades,
            twist_angle=np.degrees(self.metal_angles.stagger_angle[-1] - self.metal_angles.stagger_angle[0]),
            is_rotating=self.is_rotating,
        )
