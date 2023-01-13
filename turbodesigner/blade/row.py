from enum import Enum
from functools import cached_property
from dataclasses import dataclass
from typing import Literal, Optional
from turbodesigner.airfoils import AirfoilType, DCAAirfoil
from turbodesigner.blade.metal_angle_methods.johnsen_bullock import JohnsenBullockMetalAngleMethod
from turbodesigner.blade.metal_angles import MetalAngles
from turbodesigner.blade.vortex.common import Vortex
from turbodesigner.flow_station import FlowStation
from turbodesigner.attachments.firetree import FirtreeAttachment
import numpy as np
import numpy.typing as npt
from turbodesigner.units import MM
MetalAngleMethods = Literal["EqualsFlowAngles", "JohnsenBullock"]


@dataclass
class BladeRowCadExport:
    stage_number: int
    "stage number"

    disk_height: float
    "disk height (mm)"

    hub_radius: float
    "blade hub radius (mm)"

    tip_radius: float
    "blade hub radius (mm)"

    radii: npt.NDArray[np.float64]
    "blade station radius (mm)"

    airfoils: np.ndarray
    "airfoil coordinates for each blade radius (mm)"

    attachment: np.ndarray
    "attachment coordinates (mm)"

    attachment_with_tolerance: np.ndarray
    "attachment coordinates (mm)"

    attachment_height: float
    "attachment height (mm)"

    attachment_bottom_width: float
    "attachment bottom width (mm)"

    number_of_blades: int
    "number of blades"

    twist_angle: int
    "twist angle of blade"

    is_rotating: bool
    "whether blade is rotating or not"


@dataclass
class BladeRow:
    "calculates turbomachinery blade row"

    stage_number: int
    "stage number of blade row"

    stage_flow_station: FlowStation
    "blade stage flow station (FlowStation)"

    vortex: Vortex
    "blade vortex calculation for stagger angles"

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

    metal_angle_method: MetalAngleMethods
    "metal angle method"

    next_stage_flow_station: Optional["FlowStation"] = None
    "next blade row flow station"

    deviation_iterations: int = 20
    "nominal deviation iterations"

    def __post_init__(self):
        assert self.N_stream % 2 != 0, "N_stream must be an odd number"
        if self.is_rotating and self.next_stage_flow_station is None:
            self.next_stage_flow_station = self.stage_flow_station.copyStream(
                alpha=self.vortex.alpha(self.radii, is_rotating=False),
                radius=self.radii
            )

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
    def h_disk(self):
        "disk height of blade row (m)"
        xi = self.metal_angles.xi[0] if self.is_rotating else self.metal_angles.xi[-1]
        return np.abs(self.c*np.cos(xi) * 1.25)

    @cached_property
    def c(self):
        "chord length (m)"
        return self.h/self.AR

    @cached_property
    def tb(self):
        "blade max thickness (m)"
        return self.tbc * self.c

    @cached_property
    def Z(self):
        "number of blades in row (dimensionless)"
        Z = np.ceil(2*np.pi*self.rm/(self.sc*self.c))
        if not self.is_rotating and not Z % 2 == 0:
            Z -= 1
        return int(Z)

    @cached_property
    def s(self):
        "spacing between blades (m)"
        return 2*np.pi*self.rh/self.Z

    @cached_property
    def sh(self):
        "spacing to height (dimensionless)"
        return self.s/self.h

    @cached_property
    def sigma(self):
        "spacing between blades (dimensionless)"
        return 1 / self.sc

    @cached_property
    def deHaller(self):
        "deHaller factor (dimensionless)"
        return self.next_flow_station.W / self.flow_station.W

    @cached_property
    def Re(self):
        "Reynold's number of blade chord (dimensionless)"
        return self.stage_flow_station.rho * self.stage_flow_station.Vm * (self.c / self.stage_flow_station.mu)

    @cached_property
    def airfoil_type(self):
        # if self.stage_flow_station.MN < 0.7:
        #     return AirfoilType.NACA65
        # elif self.stage_flow_station.MN >= 0.7 and self.stage_flow_station.MN <= 1.20:
        #     return AirfoilType.DCA
        # raise ValueError("MN > 1.20 not currently supported")

        # TODO: only have support of DCA airfoil generation at the moment
        return AirfoilType.DCA

    @cached_property
    def metal_angles(self):
        if self.metal_angle_method == "JohnsenBullock":
            # beta1_rm: float = np.median(self.beta1)  # type: ignore
            # beta2_rm: float = np.median(self.beta2)  # type: ignore
            method_angle_method = JohnsenBullockMetalAngleMethod(self.beta1, self.beta2, self.sigma, self.tbc, self.airfoil_type)
            metal_angle_offset = method_angle_method.get_metal_angle_offset(self.deviation_iterations)
            return MetalAngles(self.beta1, self.beta2, metal_angle_offset.i, metal_angle_offset.delta)
        return MetalAngles(self.beta1, self.beta2, 0, 0)

    @cached_property
    def radii(self):
        "blade radii (m)"
        return np.linspace(self.rh, self.rt, self.N_stream, endpoint=True)

    @cached_property
    def flow_station(self):
        "flow station (FlowStation)"
        return self.stage_flow_station.copyStream(
            alpha=self.vortex.alpha(self.radii, self.is_rotating),
            radius=self.radii
        )

    @cached_property
    def next_flow_station(self):
        "next flow station (FlowStation)"
        assert self.next_stage_flow_station is not None
        return self.next_stage_flow_station.copyStream(
            alpha=self.vortex.alpha(self.radii, self.is_rotating),
            radius=self.radii
        )

    @cached_property
    def beta1(self):
        "blade inlet flow angle (rad)"
        if self.is_rotating:
            return self.flow_station.beta   # beta1
        return self.flow_station.alpha      # alpha2

    @cached_property
    def beta2(self):
        "blade outlet flow angle (rad)"
        if self.is_rotating:
            assert self.next_stage_flow_station is not None
            return self.next_stage_flow_station.beta                      # beta2

        assert self.next_stage_flow_station is not None or self.vortex.Rm == 0.5, "next_flow_station needs to be defined or Rc=0.5"
        if self.next_stage_flow_station is not None:
            return self.next_stage_flow_station.alpha                                    # alpha3
        return self.vortex.alpha(self.radii, is_rotating=not self.is_rotating)           # alpha3

    @cached_property
    def DF(self):
        "diffusion factor (dimensionless)"
        return 1-(np.cos(self.beta1)/np.cos(self.beta2))+(np.cos(self.beta1)/2)*self.sigma*(np.tan(self.beta1)-np.tan(self.beta2))

    @cached_property
    def airfoils(self):
        r0 = self.tb * 0.15
        # TODO: optimize this with Numba
        return [
            DCAAirfoil(self.c, self.metal_angles.theta[i], r0, self.tb, self.metal_angles.xi[i])
            for i in range(self.N_stream)
        ]

    @cached_property
    def attachment(self):
        max_length = 0.75*self.s if self.is_rotating else 1*self.s
        attachment = FirtreeAttachment(
            gamma=np.radians(40),
            beta=np.radians(40),
            ll=0.15*self.s,
            lu=0.2*self.s,
            Ri=0.05*self.s,
            Ro=0.025*self.s,
            R_dove=0.05*self.s,
            max_length=max_length,
            num_stages=2,
            disk_radius=self.rh,
            tolerance=0.0006,  # m, 0.5 mm
            include_top_arc=self.is_rotating
        )
        return attachment

    def to_cad_export(self):
        return BladeRowCadExport(
            stage_number=self.stage_number,
            disk_height=self.h_disk * MM,
            hub_radius=self.rh * MM,
            tip_radius=self.rt * MM,
            radii=self.radii * MM,
            airfoils=np.array([airfoil.get_coords() for airfoil in self.airfoils]) * MM,
            attachment=self.attachment.coords * MM,
            attachment_with_tolerance=self.attachment.coords_with_tolerance * MM,
            attachment_height=self.attachment.height * MM,
            attachment_bottom_width=self.attachment.bottom_width * MM,
            number_of_blades=self.Z,
            twist_angle=np.degrees(self.metal_angles.xi[-1]-self.metal_angles.xi[0]),
            is_rotating=self.is_rotating,
        )
