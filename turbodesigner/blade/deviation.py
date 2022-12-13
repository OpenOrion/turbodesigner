from dataclasses import dataclass
from functools import cached_property
import numpy as np
from turbodesigner.airfoils import AirfoilType

from turbodesigner.blade.metal_angles import MetalAngles

@dataclass
class BladeDeviation:

    beta1: float | np.ndarray
    "inlet flow angle (rad)"

    beta2: float | np.ndarray
    "outlet flow angle (rad)"

    sigma: float
    "spacing between blades (m)"

    tbc: float
    "max thickness to chord (dimensionless)"

    airfoil_type: AirfoilType
    "airfoil type (AirfoilType)"

    def __post_init__(self):
        self.beta1_deg = np.abs(np.degrees(self.beta1))
        self.beta2_deg = np.abs(np.degrees(self.beta2))

    @cached_property
    def Ksh(self):
        "blade shape paramter (dimensionless)"
        match self.airfoil_type:
            case AirfoilType.NACA65: return 1.0
            case AirfoilType.DCA:    return 0.7
            case AirfoilType.C4:     return 1.1

    @cached_property
    def n(self):
        "slope factor (dimensionless)"
        return 0.025*self.sigma - ((1/90)*self.beta1_deg)**(1.2*self.sigma + 1)/(0.43*self.sigma + 1.5) - 0.06

    @cached_property
    def kti(self):
        "design incidence angle correction factor (dimensionless)"
        q = 0.28/(self.tbc**0.3 + 0.1)
        return (10*self.tbc)**q

    @cached_property
    def m(self):
        "deviation slope factor (dimensionless)"
        x = (1/100)*self.beta1_deg

        match self.airfoil_type:
            case AirfoilType.NACA65:
                m1 = 0.333*x**2 - 0.0333*x + 0.17
            case _:
                m1 = 0.316*x**3 - 0.132*x**2 + 0.074*x + 0.249

        b = -0.85*x**3 - 0.17*x + 0.9625
        return self.sigma**(-b)*m1

    @cached_property
    def Ktdelta(self):
        "design deviation angle correction factor (dimensionless)"
        return 37.5*self.tbc**2 + 6.25*self.tbc

    @cached_property
    def delta_star_0_10(self):
        "nominal deviation angle theta=0, tbc=0.10 (deg)"
        return 0.01*self.beta1_deg*self.sigma + ((0.74*self.sigma**1.9) + 3*self.sigma)*(self.beta1_deg/90)**(1.09*self.sigma + 1.67)

    @cached_property
    def i_star_0_10(self):
        "nominal incidence angle theta=0, tbc=0.10 (deg)"
        # seal pitch (dimensionless)
        p = (1/160)*self.sigma**3 + 0.914 
        return ((self.beta1_deg**p)/(5 + 46*np.exp(-2.3*self.sigma))) - 0.1*self.sigma**3*np.exp((self.beta1_deg - 70)/4)

    def get_i_star_deg(self, theta_deg: float | np.ndarray):
        "nominal incidence angle (deg)"
        return theta_deg*self.n + self.kti*self.i_star_0_10*self.Ksh

    def get_delta_star_deg(self, theta_deg: float | np.ndarray):
        "nominal deviation angle (deg)"
        return self.Ksh*self.Ktdelta*self.delta_star_0_10 + theta_deg*self.m

    def get_metal_angles(self, iterations: int):
        i_star_deg, delta_star_deg = 0, 0
        beta1_deg, beta2_deg = self.beta1_deg, self.beta2_deg 
        # TODO: make this more efficient with Numba
        for _ in range(iterations):
            metal_angles_deg = MetalAngles(beta1_deg, beta2_deg, i_star_deg, delta_star_deg)
            theta_deg = np.abs(metal_angles_deg.theta)
            i_star_deg = self.get_i_star_deg(theta_deg)
            delta_star_deg = self.get_delta_star_deg(theta_deg)
            
        i = np.radians(i_star_deg) * np.sign(self.beta1)
        delta = np.radians(delta_star_deg) * np.sign(self.beta2)
        return MetalAngles(self.beta1, self.beta2, i, delta)
