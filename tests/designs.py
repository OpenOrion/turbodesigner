import numpy as np
from turbodesigner.stage import StageBladeProperty
from turbodesigner.turbomachinery import Turbomachinery

base_design = Turbomachinery(
    gamma=1.4,              # dimensionless
    cx=150,                 # m/s
    N=15000,                # rpm
    Rs=287,                 # J/(kg*K)
    mdot=20,                # kg/s
    PR=4.15,                # dimensionless
    P01=101000,             # Pa
    T01=288,                # K
    eta_isen=0.87848151,    # dimensionless
    N_stg=7,                # dimensionless
    Delta_T0_stg=np.array([20, 25, 25, 25, 25, 25, 20]),    # K
    R_stg=np.array([0.874, 0.7, 0.5, 0.5, 0.5, 0.5, 0.5]),  # dimensionless
    B_in=0,                 # m
    B_out=0,                # m
    ht=0.5,                 # dimensionless
    N_stream=3,             # dimensionless
    AR=[
        StageBladeProperty(0.5, 0.5),
        StageBladeProperty(0.5, 0.5),
        StageBladeProperty(0.5, 0.5),
        StageBladeProperty(0.5, 0.5),
        StageBladeProperty(0.5, 0.5),
        StageBladeProperty(0.5, 0.5),
        StageBladeProperty(0.5, 0.5),
    ],  # dimensionless
    sc=[
        StageBladeProperty(1.0, 1.0),
        StageBladeProperty(1.0, 1.0),
        StageBladeProperty(1.0, 1.0),
        StageBladeProperty(1.0, 1.0),
        StageBladeProperty(1.0, 1.0),
        StageBladeProperty(1.0, 1.0),
        StageBladeProperty(1.0, 1.0),
    ], # dimensionless
    tbc=[
        StageBladeProperty(0.1, 0.1),
        StageBladeProperty(0.1, 0.1),
        StageBladeProperty(0.1, 0.1),
        StageBladeProperty(0.1, 0.1),
        StageBladeProperty(0.1, 0.1),
        StageBladeProperty(0.1, 0.1),
        StageBladeProperty(0.1, 0.1),
    ], # dimensionless
)
