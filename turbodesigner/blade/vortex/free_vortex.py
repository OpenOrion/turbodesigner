from typing import Union
import numpy as np
from turbodesigner.blade.vortex.common import Vortex

class FreeVortex(Vortex):
    def ctheta(self, r: Union[float, np.ndarray], is_rotating: bool):
        mu = r / self.mean_radius
        a = self.mean_blade_velocity * (1 - self.mean_reaction)
        b = (1/2) * self.mean_loading_coefficient * self.mean_blade_velocity
        sign = -1 if is_rotating else 1
        return (a / mu) + sign * (b / mu)