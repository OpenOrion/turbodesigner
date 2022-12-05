from enum import Enum
from functools import cached_property
from dataclasses import dataclass, field
from re import I
from typing import Iterable, Optional
from turbodesigner.flow_station import FlowCalculations, FlowStation
import numpy as np
import numpy.typing as npt

class AirfoilType(Enum):
    NACA65 = 1
    DCA = 2
    C4 = 2

@dataclass
class MetalAngles:

    beta1: float | np.ndarray
    "blade inlet flow angle (rad)"

    beta2: float | np.ndarray
    "blade outlet flow angle (rad)"

    i: float | np.ndarray
    "blade incidence (rad)"

    delta: float | np.ndarray
    "blade deviation (rad)"

    kappa1: float | np.ndarray = field(init=False) 
    "inlet metal angle (rad)"

    kappa2: float | np.ndarray = field(init=False) 
    "outlet metal angle (rad)"

    theta: float | np.ndarray = field(init=False) 
    "camber angle (rad)"

    def __post_init__(self):
        self.kappa1 = self.beta1 - self.i
        self.kappa2 = self.beta2 - self.delta
        self.theta = self.kappa1-self.kappa2

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
        self.beta1_deg = np.degrees(self.beta1)
        self.beta2_deg = np.degrees(self.beta2)

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
        for _ in range(iterations):
            metal_angles_deg = MetalAngles(beta1_deg, beta2_deg, i_star_deg, delta_star_deg)
            theta_deg = metal_angles_deg.theta
            i_star_deg = self.get_i_star_deg(theta_deg)
            delta_star_deg = self.get_delta_star_deg(theta_deg)
        i = np.radians(i_star_deg)
        delta = np.radians(delta_star_deg)
        return MetalAngles(self.beta1, self.beta2, i, delta)


@dataclass
class BladeRowExport:
    stage_number: int
    "stage number"

    disk_height: float
    "disk height (length)"

    blade_height: float
    "blade height (length)"

    hub_radius: float
    "blade hub radius (length)"

    tip_radius: float
    "blade hub radius (length)"

    radii: npt.NDArray[np.float64]
    "blade station radius (length)"

    stagger_angles: npt.NDArray[np.float64]
    "stagger angle (angle)"

    camber_angles: npt.NDArray[np.float64]
    "camber angle (angle)"

    max_thickness_to_chord: npt.NDArray[np.float64]
    "max thickness to chord (dimensionless)"

    airfoil_type: AirfoilType
    "airfoil type (AirfoilType)"

    number_of_blades: int
    "number of blades"

    is_rotating: bool
    "whether blade is rotating or not"



@dataclass
class BladeRow:
    "calculates turbomachinery blade row"

    stage_flow_station: FlowStation
    "blade stage flow station (FlowStation)"

    Rc: float
    "stage reaction rate (float)"

    psi: float
    "loading coefficient (float)"

    AR: float
    "aspect ratio (dimensionless)"

    sc: float
    "spacing to chord ratio (dimensionless)"

    tbc: float
    "max thickness to chord (dimensionless)"

    is_rotating: bool
    "whether blade is rotating or not"

    N_stream: int
    "number of streams per blade (dimensionless)"

    next_blade_row: Optional["BladeRow"] = None
    "next blade row"

    deviation_iterations: int = 20
    "nominal deviation iterations"

    @cached_property
    def rt(self):
        "blade tip radius (m)"
        rt = self.stage_flow_station.outer_radius
        assert isinstance(rt, float)
        return rt

    @cached_property
    def rh(self):
        "blade hub radius (m)"
        rh = self.stage_flow_station.inner_radius
        assert isinstance(rh, float)
        return rh

    @cached_property
    def rm(self):
        "blade mean radius (m)"
        rm = self.stage_flow_station.radius
        assert isinstance(rm, float)
        return rm

    @cached_property
    def h(self):
        "height of blade (m)"
        return self.rt-self.rh

    @cached_property
    def c(self):
        "chord length (m)"
        return self.h/self.AR

    @cached_property
    def Z(self):
        "number of blades in row (dimensionless)"
        return int(np.ceil(2*np.pi*self.rm/(self.sc*self.c)))

    @cached_property
    def s(self):
        "spacing between blades (m)"
        return 2*np.pi*self.rh/self.Z

    @cached_property
    def sigma(self):
        "spacing between blades (m)"
        return 1 / self.sc

    @cached_property
    def airfoil_type(self):
        if self.stage_flow_station.MN < 0.7:
            return AirfoilType.NACA65
        elif self.stage_flow_station.MN >= 0.7 and self.stage_flow_station.MN <= 1.20:
            return AirfoilType.DCA
        raise ValueError("MN > 1.20 not currently supported")

    @cached_property
    def deviation(self):
        return BladeDeviation(self.beta1, self.beta2, self.sigma, self.tbc, self.airfoil_type)

    @cached_property
    def metal_angles(self):
        return self.deviation.get_metal_angles(self.deviation_iterations)

    @cached_property
    def radii(self):
        "blade radii"
        return np.linspace(self.rh, self.rt, self.N_stream+2, endpoint=True)

    @cached_property
    def flow_station(self):
        "flow station (FlowStation)"
        mdot_stream = self.stage_flow_station.mdot / self.N_stream
        return self.stage_flow_station.copyFlow(
            mdot=mdot_stream,
            alpha=self.alpha,
            radius=self.radii
        )

    @cached_property
    def alpha(self):
        "blade absolute flow angle(rad)"
        if self.is_rotating:
            return FlowCalculations.alpha1(self.psi, self.R, self.phi)
        return FlowCalculations.alpha2(self.psi, self.R, self.phi)

    @cached_property
    def U(self):
        "blade velocity (dimensionless)"
        return FlowCalculations.U(self.stage_flow_station.N, self.radii)

    @cached_property
    def phi(self):
        "flow coefficient (dimensionless)"
        return FlowCalculations.phi(self.stage_flow_station.Vm, self.U)

    @cached_property
    def R(self):
        "calculates free vortex blade segment reaction rate (dimensionless)"
        return -self.rm**2*(1 - self.Rc)/self.radii**2 + 1

    @cached_property
    def beta1(self):
        "blade inlet flow angle (rad)"
        if self.is_rotating:
            return FlowCalculations.beta1(self.psi, self.R, self.phi)
        return FlowCalculations.alpha2(self.psi, self.R, self.phi)
    
    @cached_property
    def beta2(self):
        "blade outlet flow angle (rad)"
        if self.is_rotating:
            return FlowCalculations.beta2(self.psi, self.R, self.phi)
        
        assert self.next_blade_row is not None or self.Rc == 0.5, "next_blade_row needs to be defined or Rc=0.5"
        if self.next_blade_row is not None:
            return FlowCalculations.alpha1(self.psi, self.next_blade_row.R, self.next_blade_row.phi)
        return FlowCalculations.alpha1(self.psi, self.R, self.phi)
