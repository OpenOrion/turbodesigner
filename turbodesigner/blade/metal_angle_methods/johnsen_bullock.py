from functools import cached_property
from typing import Union
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from turbodesigner.airfoils import AirfoilType
from turbodesigner.blade.metal_angles import MetalAngles


class MetalAngleOffset(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    i: Union[float, np.ndarray] = Field(description="Blade incidence (rad)")
    delta: Union[float, np.ndarray] = Field(description="Blade deviation (rad)")


class JohnsenBullockMetalAngleMethod(BaseModel):
    """Johnsen and Bullock 1965 metal angle method."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    inlet_flow_angle: Union[float, np.ndarray] = Field(description="Inlet flow angle (rad)")
    outlet_flow_angle: Union[float, np.ndarray] = Field(description="Outlet flow angle (rad)")
    solidity: float = Field(description="Solidity (dimensionless)")
    max_thickness_to_chord: float = Field(description="Max thickness to chord (dimensionless)")
    airfoil_type: AirfoilType = Field(description="Airfoil type")

    @cached_property
    def _inlet_angle_deg(self):
        return np.abs(np.degrees(self.inlet_flow_angle))

    @cached_property
    def _outlet_angle_deg(self):
        return np.abs(np.degrees(self.outlet_flow_angle))

    @cached_property
    def Ksh(self):
        """Blade shape parameter (dimensionless)"""
        if self.airfoil_type == AirfoilType.NACA65:
            return 1.0
        elif self.airfoil_type == AirfoilType.DCA:
            return 0.7
        elif self.airfoil_type == AirfoilType.C4:
            return 1.1
        else:
            return 1.0

    @cached_property
    def n(self):
        """Slope factor (dimensionless)"""
        return 0.025 * self.solidity - ((1/90) * self._inlet_angle_deg)**(1.2 * self.solidity + 1) / (0.43 * self.solidity + 1.5) - 0.06

    @cached_property
    def kti(self):
        """Design incidence angle correction factor (dimensionless)"""
        q = 0.28 / (self.max_thickness_to_chord**0.3 + 0.1)
        return (10 * self.max_thickness_to_chord)**q

    @cached_property
    def m(self):
        """Deviation slope factor (dimensionless)"""
        x = (1/100) * self._inlet_angle_deg
        if self.airfoil_type == AirfoilType.NACA65:
            m1 = 0.333 * x**2 - 0.0333 * x + 0.17
        else:
            m1 = 0.316 * x**3 - 0.132 * x**2 + 0.074 * x + 0.249
        b = -0.85 * x**3 - 0.17 * x + 0.9625
        return self.solidity**(-b) * m1

    @cached_property
    def Ktdelta(self):
        """Design deviation angle correction factor (dimensionless)"""
        return 37.5 * self.max_thickness_to_chord**2 + 6.25 * self.max_thickness_to_chord

    @cached_property
    def delta_star_0_10(self):
        """Nominal deviation angle theta=0, tbc=0.10 (deg)"""
        return 0.01 * self._inlet_angle_deg * self.solidity + ((0.74 * self.solidity**1.9) + 3 * self.solidity) * (self._inlet_angle_deg / 90)**(1.09 * self.solidity + 1.67)

    @cached_property
    def i_star_0_10(self):
        """Nominal incidence angle theta=0, tbc=0.10 (deg)"""
        p = (1/160) * self.solidity**3 + 0.914
        return ((self._inlet_angle_deg**p) / (5 + 46 * np.exp(-2.3 * self.solidity))) - 0.1 * self.solidity**3 * np.exp((self._inlet_angle_deg - 70) / 4)

    def get_i_star_deg(self, theta_deg: Union[float, np.ndarray]):
        """Nominal incidence angle (deg)"""
        return theta_deg * self.n + self.kti * self.i_star_0_10 * self.Ksh

    def get_delta_star_deg(self, theta_deg: Union[float, np.ndarray]):
        """Nominal deviation angle (deg)"""
        return self.Ksh * self.Ktdelta * self.delta_star_0_10 + theta_deg * self.m

    def get_metal_angle_offset(self, iterations: int) -> MetalAngleOffset:
        i_star_deg, delta_star_deg = 0, 0
        for _ in range(iterations):
            metal_angles = MetalAngles(
                inlet_flow_angle=self._inlet_angle_deg,
                outlet_flow_angle=self._outlet_angle_deg,
                incidence=i_star_deg,
                deviation=delta_star_deg,
            )
            theta_deg = metal_angles.camber_angle
            i_star_deg = self.get_i_star_deg(theta_deg)
            delta_star_deg = self.get_delta_star_deg(theta_deg)

        i = np.radians(i_star_deg) * np.sign(self.inlet_flow_angle)
        delta = np.radians(delta_star_deg) * np.sign(self.outlet_flow_angle)
        return MetalAngleOffset(i=i, delta=delta)
