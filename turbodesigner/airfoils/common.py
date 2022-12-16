from enum import Enum
import numpy as np

class AirfoilType(Enum):
    NACA65 = 1
    DCA = 2
    C4 = 2

def get_staggered_coords(coords: np.ndarray, stagger_angle: float):
    x = coords[:, 0]
    y = coords[:, 1]

    return np.array([
        x*np.cos(stagger_angle) - y*np.sin(stagger_angle),
        x*np.sin(stagger_angle) + y*np.cos(stagger_angle),
    ]).T 
