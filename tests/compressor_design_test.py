import unittest
import numpy as np
from tests.designs import base_design

class CompressorDesignTest(unittest.TestCase):
    def test_flow_station(self):
        np.testing.assert_almost_equal(base_design.outlet_flow_station.P0, 419150)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.P, 87908.56, 2)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.P, 383948.29, 2)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.T, 276.80039821)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.T, 441.27919465)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.rho, 1.10657931)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.rho, 3.03163833)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.A_flow, 0.12049144)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.A_phys, 0.12049144)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.A_flow, 0.04398062)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.A_phys, 0.044, 3)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.T0, 452.47879644)
        np.testing.assert_almost_equal(base_design.Delta_T0, 164.47879644)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.inner_radius, 0.11307, 5)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.inner_radius, 0.14897, 5)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.outer_radius, 0.22614, 5)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.outer_radius, 0.19024, 5)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.radius, 0.16960, 5)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.radius, 0.16960, 5)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.N, 15000)

    def test_stage_flow_station(self):
        next_stage = base_design.stages[1]
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.T0, 308)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.T0, 333)
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.T, 296.265, 3)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.T,  313.76513, 5)

        np.testing.assert_almost_equal(next_stage.inlet_flow_station.P0, 124787.12942, 5)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.P0, 159563.80095, 5)
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.P, 108924.147, 3)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.P, 129567.45266, 5)
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.rho, 1.281, 3)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.rho,  1.43883, 5)

        np.testing.assert_almost_equal(next_stage.inlet_flow_station.inner_radius, 0.121, 3)
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.outer_radius, 0.218, 3)
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.radius, 0.1696031)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.inner_radius, 0.12612, 5)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.outer_radius, 0.21308, 5)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.radius, 0.1696031)

if __name__ == '__main__':
    unittest.main()
