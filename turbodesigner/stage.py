from functools import cached_property
from dataclasses import dataclass
from typing import Optional
import numpy as np
from turbodesigner.blade import BladeRow, BladeRowExport
from turbodesigner.flow_station import FlowCalculations, FlowStation


@dataclass
class StageBladeProperty:
    rotor: float
    stator: float

@dataclass
class StageExport:
    rotor: BladeRowExport
    "rotor blade row"

    stator: BladeRowExport
    "stator blade row"

    stage_number: int
    "stage number"

@dataclass
class Stage:
    "calculates turbomachinery stage"

    Delta_T0: float
    "stage stagnation temperature change between inlet and outlet (K)"

    R: float
    "stage reaction (dimensionless)"

    inlet_flow_station: FlowStation
    "inlet flow station (FlowStation)"

    eta_poly: float
    "polytropic efficiency (dimensionless)"

    N_stream: int
    "number of streams per blade (dimensionless)"

    AR: StageBladeProperty
    "aspect ratio (dimensionless)"

    sc: StageBladeProperty
    "spacing to chord ratio (dimensionless)"

    tbc: StageBladeProperty
    "max thickness to chord (dimensionless)"

    next_stage: Optional["Stage"] = None
    "next turbomachinery stage"


    @cached_property
    def Delta_h(self) -> float:
        "enthalpy change between inlet and outlet (J/kg)"
        return self.Delta_T0*self.inlet_flow_station.Cp

    @cached_property
    def U(self):
        "mean blade velocity (m/s)"
        return FlowCalculations.U(self.inlet_flow_station.N, self.inlet_flow_station.radius)

    @cached_property
    def phi(self):
        "flow coefficient (dimensionless)"
        return FlowCalculations.phi(self.inlet_flow_station.Vm, self.U)

    @cached_property
    def psi(self):
        "loading coefficient (dimensionless)"
        assert isinstance(self.U, float)
        return self.Delta_h/self.U**2

    @cached_property
    def alpha1(self):
        "absolute inlet flow angle (rad)"
        return FlowCalculations.alpha1(self.psi, self.R, self.phi)

    @cached_property
    def alpha2(self):
        "absolute outlet flow angle (rad)"
        return FlowCalculations.alpha2(self.psi, self.R, self.phi)

    @cached_property
    def T02(self):
        "outlet stagnation temperature (K)"
        return self.inlet_flow_station.T0 + self.Delta_T0

    @cached_property
    def outlet_flow_station(self):
        "outlet flow station (FlowStation)"
        P02 = self.inlet_flow_station.P0*self.PR
        return self.inlet_flow_station.copyFlow(
            T0=self.T02,
            P0=P02,
            alpha=self.alpha2,
        )

    @cached_property
    def PR(self):
        "pressure ratio (dimensionless)"
        gamma = self.inlet_flow_station.gamma
        return self.TR**(self.eta_poly*gamma/(gamma - 1))

    @cached_property
    def TR(self):
        "stagnation temperature ratio between stage outlet and inlet (dimensionless)"
        return self.T02/self.inlet_flow_station.T0

    @cached_property
    def rotor(self):
        return BladeRow(
            stage_flow_station=self.inlet_flow_station,
            Rc=self.R,
            psi=self.psi,
            AR=self.AR.rotor,
            sc=self.sc.rotor,
            tbc=self.tbc.rotor,
            is_rotating=True,
            N_stream=self.N_stream,
        )

    @cached_property
    def stator(self):
        return BladeRow(
            stage_flow_station=self.outlet_flow_station,
            Rc=self.R,
            psi=self.psi,
            AR=self.AR.stator,
            sc=self.sc.stator,
            tbc=self.tbc.stator,
            is_rotating=True,
            N_stream=self.N_stream,
            next_blade_row=None if self.next_stage is None else self.next_stage.rotor
        )