from cmath import isnan
from functools import cached_property
from dataclasses import dataclass
from typing import Optional
import numpy as np
import inspect

class ThermodynamicsCalculations:
    @staticmethod
    def Cp(gamma: float, Rs: float):
        """specific heat at constant pressure (J/(kg*K))
                
        Parameters
        ==========

        gamma: float
            ratio of specific heats (dimensionless)

        Rs: float
            specific gas constant (J/(kg*K))

        """
        return Rs*gamma/(gamma - 1)

class FlowCalculations:
    @staticmethod
    def alpha1(psi: float, R: float | np.ndarray, phi: float | np.ndarray):
        """absolute flow angle at the rotor's inlet (rad)
        
        Parameters
        ==========

        psi: float
            loading coefficient (dimensionless)

        reaction: float
            reaction rate (dimensionless)

        phi: float | np.ndarray
            flow coefficient (dimensionless)
        """
        return np.arctan((-1/2*psi - R + 1)/phi)

    @staticmethod
    def beta1(psi: float, R: float | np.ndarray, phi: float | np.ndarray):
        """relative flow angle at the rotor inlet (rad)
        
        Parameters
        ==========

        psi: float
            loading coefficient (dimensionless)

        reaction: float
            reaction rate (dimensionless)

        phi: float | np.ndarray
            flow coefficient (dimensionless)
        """
        return np.arctan((1/2*psi + R)/phi)

    @staticmethod
    def beta2(psi: float, R: float | np.ndarray, phi: float | np.ndarray):
        """relative flow angle at the stator inlet (rad)
        
        Parameters
        ==========

        psi: float
            loading coefficient (dimensionless)

        reaction: float
            reaction rate (dimensionless)

        phi: float | np.ndarray
            flow coefficient (dimensionless)
        """
        return np.arctan((-1/2*psi + R)/phi)

    @staticmethod
    def alpha2(psi: float, R: float | np.ndarray, phi: float | np.ndarray):
        """absolute flow angle at the stator inlet (rad)
        
        Parameters
        ==========

        psi: float
            loading coefficient (dimensionless)

        reaction: float
            reaction rate (dimensionless)

        phi: float | np.ndarray
            flow coefficient (dimensionless)
        """

        return np.arctan(((1/2)*psi - R + 1)/phi)

    @staticmethod
    def U(N: float, r: float | np.ndarray | np.ndarray):
        """blade velocity (m/s)
        
        Parameters
        ==========

        N: float
            rotational speed (rpm)

        r: float | np.ndarray | np.ndarray
            radius (m)
        """
        return (1/30)*np.pi*N*r

    @staticmethod
    def phi(Vm: float, U: float | np.ndarray):
        """flow coefficient (dimensionless)
        
        Parameters
        ==========

        Vm: float
            meridional flow velocity (m/s)

        U: float | np.ndarray
            blade velocity (m/s)
    
        """
        return Vm/U


@dataclass
class FlowStation:
    "calculates flow station"

    gamma: float
    "ratio of specific heats (dimensionless)"

    Rs: float
    "specific gas constant (J/(kg*K))"

    T0: float
    "stagnation temperature (K)"

    P0: float
    "stagnation pressure (Pa)"

    Vm: float
    "meridional flow velocity (m/s)"

    mdot: float
    "mass flow rate (kg/s)"

    B: float = 0.0
    "blockage factor (dimensionless)"

    alpha: float | np.ndarray = np.nan
    "absolute flow angle (rad)"

    N: float = np.nan
    "rotational speed (rpm)"

    radius: float | np.ndarray = np.nan
    "flow radius (m)"

    def copyFlow(
        self, 
        T0: Optional[float] = None,
        P0: Optional[float] = None,
        mdot: Optional[float] = None,
        alpha: Optional[float | np.ndarray] = None,
        radius: Optional[float | np.ndarray] = None,
    ):
        "copies FlowStation (FlowStation)"
        return FlowStation(
            gamma=self.gamma,
            Rs=self.Rs,
            T0=self.T0 if T0 is None else T0,
            P0=self.P0 if P0 is None else P0,
            Vm=self.Vm,
            mdot=self.mdot if mdot is None else mdot,
            B=self.B,
            alpha=self.alpha if alpha is None else alpha,
            N=self.N,
            radius=self.radius if radius is None else radius
        )

    @cached_property
    def Cp(self):
        "specific heat at constant pressure (J/(kg*K))"
        return ThermodynamicsCalculations.Cp(self.gamma, self.Rs)

    @cached_property
    def T(self):
        "static fluid temperature (K)"
        V = self.c
        if np.isnan(V):
            V = self.Vm
        return self.T0 - (V**2)/(2*self.Cp)

    @cached_property
    def P(self):
        "static fluid pressure (Pa)"
        return self.P0*(self.T/self.T0)**(self.gamma/(self.gamma - 1))
    
    @cached_property
    def rho(self):
        "fluid density (kg/m**3)"
        return self.P/(self.T*self.Rs)

    @cached_property
    def q(self):
        "dynamic fluid pressure (Pa)"
        return 0.5*self.rho*self.Vm**2

    @cached_property
    def a(self):
        "speed of sound in medium (m/s)"
        return np.sqrt(self.T*self.Rs*self.gamma)
    
    @cached_property
    def MN(self):
        "mach number (dimensionless)"
        return self.Vm/self.a

    @cached_property
    def A_flow(self):
        "cross-sectional flow area (m**2)"
        return self.mdot/(self.rho*self.Vm)

    @cached_property
    def A_phys(self):
        "physical cross sectional area (m**2)"
        return self.A_flow*(self.B + 1)

    # %% Flow Properties
    @cached_property
    def U(self):
        "blade velocity (m/s)"
        return FlowCalculations.U(self.N, self.radius)

    @cached_property
    def ctheta(self):
        "absolute tangential velocity at the rotor's inlet (m/s)"
        return self.Vm*np.tan(self.alpha)

    @cached_property
    def c(self):
        "absolute flow velocity (m/s)"
        return self.Vm/np.cos(self.alpha)

    @cached_property
    def wtheta(self):
        "relative tangential flow velocity (m/s)"
        return self.ctheta - self.U

    @cached_property
    def beta(self):
        "relative flow angle (rad)"
        return np.arctan(self.wtheta/self.Vm)

    @cached_property
    def w(self):
        "relative flow velocity (m/s)"
        return self.Vm/np.cos(self.beta)

    # %% Annular Properties
    @cached_property
    def outer_radius(self):
        "flow outer radius (m)"
        return self.A_phys/(4*np.pi*self.radius) + self.radius

    @cached_property
    def inner_radius(self):
        "flow inner radius (m)"
        return 2*self.radius - self.outer_radius

    def set_radius(self, ht: float):
        """sets radius from hub to tip ratio
                
        Parameters
        ==========

        ht: float
            hub to tip ratio (dimensionless)
        """
        outer_radius = np.sqrt(self.A_phys / (np.pi*(1-ht**2)))
        inner_radius = ht * outer_radius
        self.radius = (outer_radius + inner_radius) / 2