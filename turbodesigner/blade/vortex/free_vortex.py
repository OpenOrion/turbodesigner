from functools import cached_property
import numpy as np
from turbodesigner.blade.vortex.common import Vortex

class FreeVortex(Vortex):
    def ctheta(self, r: np.ndarray | float, is_rotating: bool):
        mu = r/self.rm
        a = self.Um*(1-self.Rm)
        b = (1/2)*self.psi_m*self.Um
        sign = -1 if is_rotating else 1
        return (a/mu) + sign*(b/mu)