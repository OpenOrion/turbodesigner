from enum import Enum
import numpy as np

class AirfoilType(Enum):
    NACA65 = 1
    DCA = 2
    C4 = 2

def get_staggered_coords(coords: np.ndarray, stagger_angle: float):
    return np.array([
        coords[:, 0]*np.cos(stagger_angle) - coords[:, 1]*np.sin(stagger_angle),
        coords[:, 0]*np.sin(stagger_angle) + coords[:, 1]*np.cos(stagger_angle),
    ]).T
