from functools import cached_property
from dataclasses import dataclass
from typing import Optional
import numpy as np
from turbodesigner.blade.row import BladeRow, BladeRowCadExport, MetalAngleMethods
from turbodesigner.blade.vortex.free_vortex import FreeVortex
from turbodesigner.flow_station import FlowStation
from turbodesigner.units import MM


@dataclass
class StageBladeProperty:
    rotor: float
    stator: float


@dataclass
class StageCadExport:
    rotor: BladeRowCadExport
    "rotor blade row"

    stator: BladeRowCadExport
    "stator blade row"

    stage_height: float
    "stage height (mm)"

    stage_number: int
    "stage number"

    row_gap: float
    "stage gap (mm)"

    stage_gap: float
    "stage gap (mm)"


@dataclass
class Stage:
    "calculates turbomachinery stage"

    stage_number: int
    "stage number"

    Delta_Tt: float
    "stage stagnation temperature change between inlet and outlet (K)"

    R: float
    "stage reaction (dimensionless)"

    previous_flow_station: FlowStation
    "previous flow station (FlowStation)"

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

    rgc: float
    "row gap to chord (dimensionless)"

    sgc: float
    "stage gap to chord (dimensionless)"

    metal_angle_method: MetalAngleMethods
    "metal angle method"

    next_stage: Optional["Stage"] = None
    "next turbomachinery stage"

    def __post_init__(self):
        assert isinstance(self.previous_flow_station.radius, float)
        self.rm = self.previous_flow_station.radius
        self.N = self.previous_flow_station.N

    @cached_property
    def Delta_ht(self) -> float:
        "enthalpy change between inlet and outlet (J/kg)"
        return self.Delta_Tt*self.previous_flow_station.Cp

    @cached_property
    def U(self):
        "mean blade velocity (m/s)"
        U = FlowStation.calc_U(self.N, self.rm)
        assert isinstance(U, float)
        return U

    @cached_property
    def phi(self):
        "flow coefficient (dimensionless)"
        return self.previous_flow_station.Vm/self.U

    @cached_property
    def psi(self):
        "loading coefficient (dimensionless)"
        return self.Delta_ht/self.U**2

    @cached_property
    def Tt2(self):
        "outlet total temperature (K)"
        return self.inlet_flow_station.Tt + self.Delta_Tt

    @cached_property
    def inlet_flow_station(self):
        "mid flow station between rotor and stator (FlowStation)"
        alpha1 = np.arctan((1 - self.R + -(1/2)*self.psi)/self.phi)
        return self.previous_flow_station.copyFlow(
            alpha=alpha1,
        )

    @cached_property
    def mid_flow_station(self):
        "mid flow station between rotor and stator (FlowStation)"
        alpha2 = np.arctan((1 - self.R + (1/2)*self.psi)/self.phi)
        Pt2 = self.inlet_flow_station.Pt*self.PR
        return self.inlet_flow_station.copyFlow(
            Tt=self.Tt2,
            Pt=Pt2,
            alpha=alpha2,
        )

    @cached_property
    def PR(self):
        "pressure ratio (dimensionless)"
        gamma = self.inlet_flow_station.gamma
        return self.TR**(self.eta_poly*gamma/(gamma - 1))

    @cached_property
    def TR(self):
        "stagnation temperature ratio between stage outlet and inlet (dimensionless)"
        return self.Tt2/self.inlet_flow_station.Tt

    @cached_property
    def tau(self):
        "torque transmitted to stage (N*m)"
        return self.inlet_flow_station.mdot*self.rm*(self.mid_flow_station.Vtheta - self.inlet_flow_station.Vtheta)

    @cached_property
    def vortex(self):
        return FreeVortex(
            Um=self.U,
            Vm=self.previous_flow_station.Vm,
            Rm=self.R,
            psi_m=self.psi,
            rm=self.rm
        )

    @cached_property
    def rotor(self):
        return BladeRow(
            stage_number=self.stage_number,
            stage_flow_station=self.inlet_flow_station,
            vortex=self.vortex,
            AR=self.AR.rotor,
            sc=self.sc.rotor,
            tbc=self.tbc.rotor,
            is_rotating=True,
            N_stream=self.N_stream,
            metal_angle_method=self.metal_angle_method,
            next_stage_flow_station=self.stator.flow_station
        )

    @cached_property
    def stator(self):
        return BladeRow(
            stage_number=self.stage_number,
            stage_flow_station=self.mid_flow_station,
            vortex=self.vortex,
            AR=self.AR.stator,
            sc=self.sc.stator,
            tbc=self.tbc.stator,
            is_rotating=False,
            N_stream=self.N_stream,
            metal_angle_method=self.metal_angle_method,
            next_stage_flow_station=None if self.next_stage is None else self.next_stage.rotor.flow_station
        )

    def to_cad_export(self):
        rotor = self.rotor.to_cad_export()
        stator = self.stator.to_cad_export()
        stage_height = rotor.disk_height+stator.disk_height
        return StageCadExport(
            stage_number=self.stage_number,
            rotor=rotor,
            stator=stator,
            stage_height=stage_height,
            stage_gap=self.sgc*self.rotor.c*MM,
            row_gap=self.rgc*self.rotor.c*MM
        )
