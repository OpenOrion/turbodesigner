import unittest
import numpy as np
from turbodesigner.stage import StageBladeProperty
from turbodesigner.turbomachinery import Turbomachinery

compressor = Turbomachinery(
    gamma=1.4,              # dimensionless
    cx=150,                 # m/s
    N=14779.74357665,       # rpm
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


class CompressorDesignTest(unittest.TestCase):
    def test_flow_station(self):
        self.assertAlmostEqual(compressor.outlet_flow_station.P0, 419150)
        self.assertAlmostEqual(compressor.inlet_flow_station.P, 87908.56, 2)
        self.assertAlmostEqual(compressor.outlet_flow_station.P, 383948.29, 2)
        self.assertAlmostEqual(compressor.inlet_flow_station.T, 276.80039821)
        self.assertAlmostEqual(compressor.outlet_flow_station.T, 441.27919465)
        self.assertAlmostEqual(compressor.inlet_flow_station.rho, 1.10657931)
        self.assertAlmostEqual(compressor.outlet_flow_station.rho, 3.03163833)
        self.assertAlmostEqual(compressor.inlet_flow_station.A_flow, 0.12049144)
        self.assertAlmostEqual(compressor.inlet_flow_station.A_phys, 0.12049144)
        self.assertAlmostEqual(compressor.outlet_flow_station.A_flow, 0.04398062)
        self.assertAlmostEqual(compressor.outlet_flow_station.A_phys, 0.044, 3)
        self.assertAlmostEqual(compressor.outlet_flow_station.T0, 452.47879644)
        self.assertAlmostEqual(compressor.Delta_T0, 164.47879644)
        self.assertAlmostEqual(compressor.inlet_flow_station.inner_radius, 0.11307, 5)
        self.assertAlmostEqual(compressor.outlet_flow_station.inner_radius, 0.14897, 5)
        self.assertAlmostEqual(compressor.inlet_flow_station.outer_radius, 0.22614, 5)
        self.assertAlmostEqual(compressor.outlet_flow_station.outer_radius, 0.19024, 5)
        self.assertAlmostEqual(compressor.inlet_flow_station.radius, 0.16960, 5)
        self.assertAlmostEqual(compressor.outlet_flow_station.radius, 0.16960, 5)
        self.assertAlmostEqual(compressor.inlet_flow_station.N, 14779.74357665)

    def test_stage_flow_station(self):
        next_stage = compressor.stages[1]
        self.assertAlmostEqual(next_stage.inlet_flow_station.T0, 308)
        self.assertAlmostEqual(next_stage.outlet_flow_station.T0, 333)
        self.assertAlmostEqual(next_stage.inlet_flow_station.T, 294.26698, 5)
        self.assertAlmostEqual(next_stage.outlet_flow_station.T, 313.82462, 5)

        self.assertAlmostEqual(next_stage.inlet_flow_station.P0, 124787.12942, 5)
        self.assertAlmostEqual(next_stage.outlet_flow_station.P0, 159563.80095, 5)
        self.assertAlmostEqual(next_stage.inlet_flow_station.P, 106374.53118, 5)
        self.assertAlmostEqual(next_stage.outlet_flow_station.P, 129653.45430, 5)
        self.assertAlmostEqual(next_stage.inlet_flow_station.rho, 1.25955, 5)
        self.assertAlmostEqual(next_stage.outlet_flow_station.rho, 1.43951, 5)

        self.assertAlmostEqual(next_stage.inlet_flow_station.inner_radius, 0.11993, 5)
        self.assertAlmostEqual(next_stage.inlet_flow_station.outer_radius, 0.21927, 5)
        self.assertAlmostEqual(next_stage.inlet_flow_station.radius, 0.1696031)
        self.assertAlmostEqual(next_stage.outlet_flow_station.inner_radius, 0.12614, 5)
        self.assertAlmostEqual(next_stage.outlet_flow_station.outer_radius, 0.21306, 5)
        self.assertAlmostEqual(next_stage.outlet_flow_station.radius, 0.1696031)

if __name__ == '__main__':
    unittest.main()
