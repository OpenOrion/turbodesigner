from functools import cached_property
from typing import Optional, Union
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, computed_field

PROP_NON_STREAM_ERROR = "Property not allowed with streams"


class FluidConstants:
    MU_REF = 1.73E-5
    "reference dynamic viscosity at sea level ((N*s)/m**2)"

    PT_REF = 101325
    "reference pressure at sea level (Pa)"

    T0_REF = 288.15
    "reference temperature at sea level (K)"

    C = 110.4
    "sutherland constant (K)"


class FlowStation(BaseModel):
    """Calculates flow station for an ideal gas."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=False)

    gamma: float = Field(default=float('nan'), description="Ratio of specific heats (dimensionless)")

    gas_constant: float = Field(default=float('nan'), description="Specific gas constant (J/(kg*K))")

    total_temperature: float = Field(default=float('nan'), description="Total temperature (K)")

    total_pressure: float = Field(default=float('nan'), description="Total pressure (Pa)")

    meridional_velocity: float = Field(default=float('nan'), description="Meridional flow velocity (m/s)")

    mass_flow_rate: float = Field(default=float('nan'), description="Mass flow rate (kg/s)")

    blockage: float = Field(default=0.0, description="Blockage factor (dimensionless)")

    flow_angle: Union[float, np.ndarray] = Field(default=float('nan'), description="Absolute flow angle (rad)")

    rpm: float = Field(default=float('nan'), description="Rotational speed (rpm)")

    radius: Union[float, np.ndarray] = Field(default=float('nan'), description="Flow radius (m)")

    mixture: str = Field(default="Air", description="Gas mixture")

    is_stream: bool = Field(default=False, description="Whether station is 1D stream")

    def copy_flow(
        self,
        total_temperature: Optional[float] = None,
        total_pressure: Optional[float] = None,
        meridional_velocity: Optional[float] = None,
        mass_flow_rate: Optional[float] = None,
        flow_angle: Optional[Union[float, np.ndarray]] = None,
        radius: Optional[Union[float, np.ndarray]] = None,
    ) -> "FlowStation":
        """Copy all elements of FlowStation with optional overrides."""
        return FlowStation(
            gamma=self.gamma,
            gas_constant=self.gas_constant,
            total_temperature=self.total_temperature if total_temperature is None else total_temperature,
            total_pressure=self.total_pressure if total_pressure is None else total_pressure,
            meridional_velocity=self.meridional_velocity if meridional_velocity is None else meridional_velocity,
            mass_flow_rate=self.mass_flow_rate if mass_flow_rate is None else mass_flow_rate,
            blockage=self.blockage,
            flow_angle=self.flow_angle if flow_angle is None else flow_angle,
            rpm=self.rpm,
            radius=self.radius if radius is None else radius,
            mixture=self.mixture,
        )

    def copy_stream(
        self,
        flow_angle: Optional[Union[float, np.ndarray]] = None,
        radius: Optional[Union[float, np.ndarray]] = None,
    ) -> "FlowStation":
        """Copy stream elements (excludes mass flow rate)."""
        return FlowStation(
            gamma=self.gamma,
            gas_constant=self.gas_constant,
            total_temperature=self.total_temperature,
            total_pressure=self.total_pressure,
            meridional_velocity=self.meridional_velocity,
            flow_angle=self.flow_angle if flow_angle is None else flow_angle,
            rpm=self.rpm,
            radius=self.radius if radius is None else radius,
            is_stream=True,
            mixture=self.mixture,
        )

    @cached_property
    def static_enthalpy(self):
        """Static enthalpy (J/kg)"""
        return self.static_temperature * self.specific_heat

    @cached_property
    def total_enthalpy(self):
        """Total enthalpy (J/kg)"""
        return self.static_enthalpy + (self.absolute_velocity**2) / 2

    @cached_property
    def specific_heat(self):
        """Specific heat at constant pressure (J/(kg*K))"""
        return self.gas_constant * self.gamma / (self.gamma - 1)

    @cached_property
    def static_temperature(self):
        """Static temperature (K)"""
        return self.total_temperature - (self.absolute_velocity**2) / (2 * self.specific_heat)

    @cached_property
    def relative_total_temperature(self):
        """Total relative temperature (K)"""
        return self.total_temperature + (self.relative_velocity**2 - self.absolute_velocity**2) / (2 * self.specific_heat)

    @cached_property
    def static_pressure(self):
        """Static pressure (Pa)"""
        return self.total_pressure * (self.static_temperature / self.total_temperature)**(self.gamma / (self.gamma - 1))

    @cached_property
    def relative_total_pressure(self):
        """Total relative pressure (Pa)"""
        return self.total_pressure * (self.relative_total_temperature / self.total_temperature)**(self.gamma / (self.gamma - 1))

    @cached_property
    def density(self):
        """Density (kg/m**3)"""
        return self.static_pressure / (self.static_temperature * self.gas_constant)

    @cached_property
    def dynamic_pressure(self):
        """Dynamic pressure (Pa)"""
        return 0.5 * self.density * self.meridional_velocity**2

    @cached_property
    def speed_of_sound(self):
        """Speed of sound (m/s)"""
        return np.sqrt(self.static_temperature * self.gas_constant * self.gamma)

    @cached_property
    def dynamic_viscosity(self):
        """Dynamic viscosity using Sutherland's formula ((N*s)/m**2)"""
        return FluidConstants.MU_REF * ((self.static_temperature / FluidConstants.T0_REF)**1.5) * ((FluidConstants.T0_REF + FluidConstants.C) / (self.static_temperature + FluidConstants.C))

    @cached_property
    def mach_number(self):
        """Mach number (dimensionless)"""
        return self.meridional_velocity / self.speed_of_sound

    @cached_property
    def critical_velocity(self):
        """Critical velocity (m/s)"""
        return np.sqrt(((2 * self.gamma) / (self.gamma + 1)) * self.gas_constant * self.total_temperature)

    @cached_property
    def blade_velocity(self):
        """Blade velocity (m/s)"""
        return FlowStation.calc_U(self.rpm, self.radius)

    @cached_property
    def angular_velocity(self):
        """Angular velocity (rad/s)"""
        return self.blade_velocity / self.radius

    @cached_property
    def tangential_velocity(self):
        """Absolute tangential velocity (m/s)"""
        return self.meridional_velocity * np.tan(self.flow_angle)

    @cached_property
    def absolute_velocity(self):
        """Absolute flow velocity (m/s)"""
        if np.isnan(self.flow_angle).all():
            return self.meridional_velocity
        return self.meridional_velocity / np.cos(self.flow_angle)

    @cached_property
    def relative_tangential_velocity(self):
        """Relative tangential flow velocity (m/s)"""
        return self.tangential_velocity - self.blade_velocity

    @cached_property
    def relative_flow_angle(self):
        """Relative flow angle (rad)"""
        return np.arctan(self.relative_tangential_velocity / self.meridional_velocity)

    @cached_property
    def relative_velocity(self):
        """Relative flow velocity (m/s)"""
        return self.meridional_velocity / np.cos(self.relative_flow_angle)

    # Annular Properties
    @cached_property
    def flow_area(self):
        """Cross-sectional flow area (m**2)"""
        assert not self.is_stream, PROP_NON_STREAM_ERROR
        return self.mass_flow_rate / (self.density * self.meridional_velocity)

    @cached_property
    def physical_area(self):
        """Physical cross-sectional area (m**2)"""
        return self.flow_area * (self.blockage + 1)

    @cached_property
    def outer_radius(self):
        """Flow outer radius (m)"""
        assert not self.is_stream, PROP_NON_STREAM_ERROR
        return self.physical_area / (4 * np.pi * self.radius) + self.radius

    @cached_property
    def inner_radius(self):
        """Flow inner radius (m)"""
        assert not self.is_stream, PROP_NON_STREAM_ERROR
        return 2 * self.radius - self.outer_radius

    @staticmethod
    def calc_radius_from_ht(ht: float, A_phys: Union[float, np.ndarray]):
        """Calculate radius from hub-to-tip ratio.

        Parameters
        ----------
        ht : float
            Hub-to-tip ratio (dimensionless)
        A_phys : float
            Physical cross-sectional area (m**2)
        """
        outer_radius = np.sqrt(A_phys / (np.pi * (1 - ht**2)))
        inner_radius = ht * outer_radius
        return (outer_radius + inner_radius) / 2

    @staticmethod
    def calc_U(N: float, radius: Union[float, np.ndarray]):
        """Calculate blade velocity.

        Parameters
        ----------
        N : float
            Rotational speed (rpm)
        radius : float
            Blade radius (m)
        """
        return 2 * np.pi * N * radius / 60

    def set_radius(self, ht: float):
        """Set radius from hub-to-tip ratio.

        Parameters
        ----------
        ht : float
            Hub-to-tip ratio (dimensionless)
        """
        self.radius = FlowStation.calc_radius_from_ht(ht, self.physical_area)
