from dataclasses import dataclass, field
from functools import cached_property
import numpy as np

@dataclass
class Vortex:
    Um: float
    "mean blade velocity (m/s)"

    Vm: float
    "meridional flow velocity (m/s)"

    Rm: float
    "mean reaction rate (dimensionless)"

    psi_m: float
    "mean loading coefficient (dimensionless)"

    rm: float
    "mean radius (m)"

    def __post_init__(self):
        self.phi_m = self.Vm/self.Um

    def ctheta(self, r: np.ndarray | float, is_rotating: bool):
        "absolute tangential velocity (m/s)"
        return np.nan

    def alpha(self, r: np.ndarray | float, is_rotating: bool):
        "absolute flow angle (rad)"
        return np.arctan(self.ctheta(r, is_rotating)/self.Vm)