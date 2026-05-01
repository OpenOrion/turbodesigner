from functools import cached_property
from typing import Optional
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from turbodesigner.blade.row import BladeRow, BladeRowCadExport, MetalAngleMethods
from turbodesigner.blade.vortex.free_vortex import FreeVortex
from turbodesigner.flow_station import FlowStation
from turbodesigner.units import MM


class StageBladeProperty(BaseModel):
    rotor: float = Field(description="Rotor value")
    stator: float = Field(description="Stator value")


class StageCadExport(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    rotor: BladeRowCadExport = Field(description="Rotor blade row CAD export")
    stator: BladeRowCadExport = Field(description="Stator blade row CAD export")
    stage_height: float = Field(description="Stage height (mm)")
    stage_number: int = Field(description="Stage number")
    row_gap: float = Field(description="Row gap (mm)")
    stage_gap: float = Field(description="Stage gap (mm)")


class Stage(BaseModel):
    """Calculates turbomachinery stage."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=False)

    stage_number: int = Field(description="Stage number")

    temperature_rise: float = Field(description="Stage stagnation temperature rise (K)")

    reaction: float = Field(description="Stage reaction (dimensionless)")

    previous_flow_station: FlowStation = Field(description="Previous flow station", exclude=True)

    polytropic_efficiency: float = Field(description="Polytropic efficiency (dimensionless)")

    num_streams: int = Field(description="Number of streams per blade (dimensionless)")

    aspect_ratio: StageBladeProperty = Field(description="Aspect ratio (dimensionless)")

    spacing_to_chord: StageBladeProperty = Field(description="Spacing to chord ratio (dimensionless)")

    max_thickness_to_chord: StageBladeProperty = Field(description="Max thickness to chord (dimensionless)")

    row_gap_to_chord: float = Field(description="Row gap to chord (dimensionless)")

    stage_gap_to_chord: float = Field(description="Stage gap to chord (dimensionless)")

    metal_angle_method: MetalAngleMethods = Field(description="Metal angle method")

    next_stage: Optional["Stage"] = Field(default=None, exclude=True)

    @cached_property
    def mean_radius(self) -> float:
        """Mean radius (m)"""
        r = self.previous_flow_station.radius
        assert isinstance(r, float)
        return r

    @cached_property
    def enthalpy_rise(self) -> float:
        """Enthalpy rise (J/kg)"""
        return self.temperature_rise * self.previous_flow_station.specific_heat

    @cached_property
    def blade_velocity(self) -> float:
        """Mean blade velocity (m/s)"""
        U = FlowStation.calc_U(self.previous_flow_station.rpm, self.mean_radius)
        assert isinstance(U, float)
        return U

    @cached_property
    def flow_coefficient(self) -> float:
        """Flow coefficient (dimensionless)"""
        return self.previous_flow_station.meridional_velocity / self.blade_velocity

    @cached_property
    def loading_coefficient(self) -> float:
        """Loading coefficient (dimensionless)"""
        return self.enthalpy_rise / self.blade_velocity**2

    @cached_property
    def outlet_total_temperature(self) -> float:
        """Outlet total temperature (K)"""
        return float(self.inlet_flow_station.total_temperature + self.temperature_rise)

    @cached_property
    def inlet_flow_station(self) -> FlowStation:
        """Inlet flow station (FlowStation)"""
        alpha1 = np.arctan((1 - self.reaction + -(1/2) * self.loading_coefficient) / self.flow_coefficient)
        return self.previous_flow_station.copy_flow(
            flow_angle=alpha1,
        )

    @cached_property
    def mid_flow_station(self) -> FlowStation:
        """Mid flow station between rotor and stator (FlowStation)"""
        alpha2 = np.arctan((1 - self.reaction + (1/2) * self.loading_coefficient) / self.flow_coefficient)
        Pt2 = self.inlet_flow_station.total_pressure * self.pressure_ratio
        return self.inlet_flow_station.copy_flow(
            total_temperature=self.outlet_total_temperature,
            total_pressure=Pt2,
            flow_angle=alpha2,
        )

    @cached_property
    def pressure_ratio(self) -> float:
        """Stage pressure ratio (dimensionless)"""
        gamma = self.inlet_flow_station.gamma
        return float(self.temperature_ratio**(self.polytropic_efficiency * gamma / (gamma - 1)))

    @cached_property
    def temperature_ratio(self) -> float:
        """Stage temperature ratio (dimensionless)"""
        return float(self.outlet_total_temperature / self.inlet_flow_station.total_temperature)

    @cached_property
    def torque(self) -> float:
        """Torque transmitted to stage (N*m)"""
        return float(self.inlet_flow_station.mass_flow_rate * self.mean_radius * (self.mid_flow_station.tangential_velocity - self.inlet_flow_station.tangential_velocity))

    @cached_property
    def vortex(self) -> FreeVortex:
        return FreeVortex(
            mean_blade_velocity=self.blade_velocity,
            meridional_velocity=self.previous_flow_station.meridional_velocity,
            mean_reaction=self.reaction,
            mean_loading_coefficient=self.loading_coefficient,
            mean_radius=self.mean_radius,
        )

    @cached_property
    def rotor(self) -> BladeRow:
        return BladeRow(
            stage_number=self.stage_number,
            stage_flow_station=self.inlet_flow_station,
            vortex=self.vortex,
            aspect_ratio=self.aspect_ratio.rotor,
            spacing_to_chord=self.spacing_to_chord.rotor,
            max_thickness_to_chord=self.max_thickness_to_chord.rotor,
            is_rotating=True,
            num_streams=self.num_streams,
            metal_angle_method=self.metal_angle_method,
            next_stage_flow_station=self.stator.flow_station,
        )

    @cached_property
    def stator(self) -> BladeRow:
        return BladeRow(
            stage_number=self.stage_number,
            stage_flow_station=self.mid_flow_station,
            vortex=self.vortex,
            aspect_ratio=self.aspect_ratio.stator,
            spacing_to_chord=self.spacing_to_chord.stator,
            max_thickness_to_chord=self.max_thickness_to_chord.stator,
            is_rotating=False,
            num_streams=self.num_streams,
            metal_angle_method=self.metal_angle_method,
            next_stage_flow_station=None if self.next_stage is None else self.next_stage.rotor.flow_station,
        )

    def to_cad_export(self) -> StageCadExport:
        rotor = self.rotor.to_cad_export()
        stator = self.stator.to_cad_export()
        stage_height = rotor.disk_height + stator.disk_height
        return StageCadExport(
            stage_number=self.stage_number,
            rotor=rotor,
            stator=stator,
            stage_height=stage_height,
            stage_gap=self.stage_gap_to_chord * self.rotor.chord * MM,
            row_gap=self.row_gap_to_chord * self.rotor.chord * MM,
        )
