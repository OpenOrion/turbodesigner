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

    phi_m: float
    "mean flow coefficient (dimensionless)"

    psi_m: float
    "mean loading coefficient (dimensionless)"

    rm: float
    "mean radius (m)"

    def ctheta(self, r: np.ndarray, is_rotating: bool):
        "absolute tangential velocity (m/s)"
        return np.nan

    def alpha(self, r: np.ndarray, is_rotating: bool):
        "absolute flow angle (rad)"
        return np.arctan(self.ctheta(r, is_rotating)/self.Vm)