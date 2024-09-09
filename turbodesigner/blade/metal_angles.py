from dataclasses import dataclass, field
from typing import Union
import numpy as np
from turbodesigner.units import DEG

@dataclass
class MetalAngles:

    beta1: Union[float, np.ndarray]
    "blade inlet flow angle (rad)"

    beta2: Union[float, np.ndarray]
    "blade outlet flow angle (rad)"

    i: Union[float, np.ndarray]
    "blade incidence (rad)"

    delta: Union[float, np.ndarray]
    "blade deviation (rad)"

    kappa1: np.ndarray = field(init=False) 
    "inlet metal angle (rad)"

    kappa2: np.ndarray = field(init=False) 
    "outlet metal angle (rad)"

    theta: np.ndarray = field(init=False) 
    "camber angle (rad)"

    xi: np.ndarray = field(init=False) 
    "stagger angle (rad)"

    def __post_init__(self):
        self.kappa1 = np. asarray(self.beta1 - self.i)
        self.kappa2 = np. asarray(self.beta2 - self.delta)
        self.theta = np. asarray(self.kappa1-self.kappa2)
        self.xi = np. asarray((self.kappa1 + self.kappa2)/2)