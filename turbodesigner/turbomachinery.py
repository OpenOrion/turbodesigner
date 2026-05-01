from functools import cached_property
import json
from typing import Literal, Union
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from turbodesigner.blade.row import MetalAngleMethods
from turbodesigner.flow_station import FlowStation
from turbodesigner.stage import Stage, StageBladeProperty, StageCadExport

Number = Union[int, float]


class TurbomachineryCadExport(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    stages: list[StageCadExport] = Field(description="Turbomachinery stages")


class Turbomachinery(BaseModel):
    model_config = ConfigDict(frozen=False)

    gamma: float = Field(description="Ratio of specific heats (dimensionless)")

    axial_velocity: float = Field(description="Axial flow velocity through the machine (m/s)")

    rpm: float = Field(description="Rotational speed (rev/min)")

    gas_constant: float = Field(description="Specific gas constant (J/(kg·K))")

    mass_flow_rate: float = Field(description="Mass flow rate (kg/s)")

    pressure_ratio: float = Field(description="Overall total pressure ratio (dimensionless)")

    inlet_total_pressure: float = Field(description="Inlet total (stagnation) pressure (Pa)")

    inlet_total_temperature: float = Field(description="Inlet total (stagnation) temperature (K)")

    isentropic_efficiency: float = Field(description="Overall isentropic efficiency (dimensionless)")

    num_stages: int = Field(description="Number of compressor stages")

    inlet_blockage: Union[Number, list[Number]] = Field(description="Inlet blockage factor (dimensionless). Single value or per-stage array")

    outlet_blockage: Union[Number, list[Number]] = Field(description="Outlet blockage factor (dimensionless). Single value or per-stage array")

    hub_to_tip_ratio: float = Field(description="Hub-to-tip radius ratio at inlet (dimensionless)")

    num_streams: int = Field(description="Number of spanwise stream tubes for radial analysis (must be odd)")

    stage_temperature_rise: Union[list[float], Literal["equal"]] = Field(description="'equal' for uniform distribution, or array of per-stage temperature rises (K)")

    stage_reaction: Union[Number, list[Number]] = Field(description="Stage reaction degree (dimensionless). Single value or per-stage array")

    row_gap_to_chord: Union[Number, list[Number]] = Field(description="Axial gap between rotor and stator as fraction of chord (dimensionless)")

    stage_gap_to_chord: Union[Number, list[Number]] = Field(description="Axial gap between stages as fraction of chord (dimensionless)")

    aspect_ratio: Union[StageBladeProperty, list[StageBladeProperty]] = Field(description="Blade aspect ratio (dimensionless). Single {rotor, stator} or per-stage array")

    spacing_to_chord: Union[StageBladeProperty, list[StageBladeProperty]] = Field(description="Blade pitch-to-chord ratio (dimensionless). Single {rotor, stator} or per-stage array")

    max_thickness_to_chord: Union[StageBladeProperty, list[StageBladeProperty]] = Field(description="Max blade thickness to chord ratio (dimensionless). Single {rotor, stator} or per-stage array")

    metal_angle_method: MetalAngleMethods = Field(default="JohnsenBullock", description="Metal angle calculation method")

    # --- Computed outputs ---

    @cached_property
    def polytropic_efficiency(self) -> float:
        """Polytropic efficiency (dimensionless)"""
        return float((self.gamma - 1) * np.log(self.pressure_ratio) / (self.gamma * np.log((self.isentropic_efficiency + self.pressure_ratio**((self.gamma - 1) / self.gamma) - 1) / self.isentropic_efficiency)))

    @cached_property
    def outlet_total_temperature(self) -> float:
        """Outlet total temperature (K)"""
        return float(self.inlet_total_temperature * self.pressure_ratio**((self.gamma - 1) / (self.polytropic_efficiency * self.gamma)))

    @cached_property
    def outlet_total_pressure(self) -> float:
        """Outlet total pressure (Pa)"""
        return float(self.inlet_total_pressure * self.pressure_ratio)

    @cached_property
    def overall_temperature_rise(self) -> float:
        """Overall temperature rise (K)"""
        return float(self.outlet_total_temperature - self.inlet_total_temperature)

    @cached_property
    def temperature_ratio(self) -> float:
        """Temperature ratio (dimensionless)"""
        return float(self.outlet_total_temperature / self.inlet_total_temperature)

    @cached_property
    def inlet_hub_radius(self) -> float:
        """Inlet hub radius (m)"""
        return float(self.inlet_flow_station.inner_radius)

    @cached_property
    def inlet_tip_radius(self) -> float:
        """Inlet tip radius (m)"""
        return float(self.inlet_flow_station.outer_radius)

    @cached_property
    def inlet_mean_radius(self) -> float:
        """Inlet mean radius (m)"""
        return float(self.inlet_flow_station.radius)

    @cached_property
    def inlet_mach_number(self) -> float:
        """Inlet Mach number (dimensionless)"""
        return float(self.inlet_flow_station.mach_number)

    @cached_property
    def inlet_mean_blade_speed(self) -> float:
        """Inlet mean blade speed (m/s)"""
        return float(self.inlet_flow_station.blade_velocity)

    # --- Internal computed properties ---

    @cached_property
    def inlet_flow_station(self) -> FlowStation:
        flow_station = FlowStation(
            gamma=self.gamma,
            gas_constant=self.gas_constant,
            total_temperature=self.inlet_total_temperature,
            total_pressure=self.inlet_total_pressure,
            meridional_velocity=self.axial_velocity,
            mass_flow_rate=self.mass_flow_rate,
            blockage=self.inlet_blockage[0] if isinstance(self.inlet_blockage, list) else self.inlet_blockage,
            rpm=self.rpm,
        )
        flow_station.set_radius(self.hub_to_tip_ratio)
        return flow_station

    @cached_property
    def outlet_flow_station(self) -> FlowStation:
        return FlowStation(
            gamma=self.gamma,
            gas_constant=self.gas_constant,
            total_temperature=self.outlet_total_temperature,
            total_pressure=self.outlet_total_pressure,
            meridional_velocity=self.axial_velocity,
            mass_flow_rate=self.mass_flow_rate,
            blockage=self.outlet_blockage[-1] if isinstance(self.outlet_blockage, list) else self.outlet_blockage,
            rpm=self.rpm,
            radius=self.inlet_flow_station.radius,
        )

    @cached_property
    def stages(self) -> list[Stage]:
        if isinstance(self.stage_temperature_rise, list):
            assert len(self.stage_temperature_rise) == self.num_stages, "stage_temperature_rise length does not equal num_stages"
        else:
            assert self.stage_temperature_rise == "equal", f"'{self.stage_temperature_rise}' for stage_temperature_rise is invalid"

        if isinstance(self.stage_reaction, list):
            assert len(self.stage_reaction) == self.num_stages, "stage_reaction length does not equal num_stages"
            assert self.stage_reaction[self.num_stages - 1] == 0.5, "Last stage reaction only supports R=0.5"
        else:
            assert self.stage_reaction == 0.5, "Last stage reaction only supports R=0.5"

        if isinstance(self.aspect_ratio, list):
            assert len(self.aspect_ratio) == self.num_stages, "aspect_ratio length does not equal num_stages"
        if isinstance(self.spacing_to_chord, list):
            assert len(self.spacing_to_chord) == self.num_stages, "spacing_to_chord length does not equal num_stages"
        if isinstance(self.max_thickness_to_chord, list):
            assert len(self.max_thickness_to_chord) == self.num_stages, "max_thickness_to_chord length does not equal num_stages"

        previous_flow_station = self.inlet_flow_station
        stages: list[Stage] = []
        for i in range(self.num_stages):
            stage = Stage(
                stage_number=i + 1,
                temperature_rise=self.stage_temperature_rise[i] if isinstance(self.stage_temperature_rise, list) else self.overall_temperature_rise / self.num_stages,
                reaction=self.stage_reaction[i] if isinstance(self.stage_reaction, list) else self.stage_reaction,
                previous_flow_station=previous_flow_station,
                polytropic_efficiency=self.polytropic_efficiency,
                num_streams=self.num_streams,
                aspect_ratio=self.aspect_ratio[i] if isinstance(self.aspect_ratio, list) else self.aspect_ratio,
                spacing_to_chord=self.spacing_to_chord[i] if isinstance(self.spacing_to_chord, list) else self.spacing_to_chord,
                max_thickness_to_chord=self.max_thickness_to_chord[i] if isinstance(self.max_thickness_to_chord, list) else self.max_thickness_to_chord,
                row_gap_to_chord=self.row_gap_to_chord[i] if isinstance(self.row_gap_to_chord, list) else self.row_gap_to_chord,
                stage_gap_to_chord=self.stage_gap_to_chord[i] if isinstance(self.stage_gap_to_chord, list) else self.stage_gap_to_chord,
                metal_angle_method=self.metal_angle_method,
            )
            previous_flow_station = stage.mid_flow_station
            if i > 0 and i < self.num_stages:
                stages[i - 1].next_stage = stage
            stages.append(stage)

        return stages

    def to_cad_export(self) -> TurbomachineryCadExport:
        return TurbomachineryCadExport(
            stages=[stage.to_cad_export() for stage in self.stages]
        )

    @staticmethod
    def from_dict(obj) -> "Turbomachinery":
        return Turbomachinery.model_validate(obj)

    @staticmethod
    def from_file(file_name: str) -> "Turbomachinery":
        from turbodesigner.cli.state import TurboDesign
        return TurboDesign.from_file(file_name).definition
