from dataclasses import dataclass, field
import numpy as np

@dataclass
class MetalAngles:

    beta1: float | np.ndarray
    "blade inlet flow angle (rad)"

    beta2: float | np.ndarray
    "blade outlet flow angle (rad)"

    i: float | np.ndarray
    "blade incidence (rad)"

    delta: float | np.ndarray
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
        self.kappa1 = np.asfarray(self.beta1 - self.i)
        self.kappa2 = np.asfarray(self.beta2 - self.delta)
        self.theta = np.asfarray(self.kappa1-self.kappa2)
        self.xi = np.asfarray((self.kappa1 + self.kappa2)/2)
