import unittest
import numpy as np
from tests.designs import base_design


class CompressorStageTest(unittest.TestCase):
    def test_first_stage_base_design(self):
        next_stage = base_design.stages[1]
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.total_temperature, 308)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.total_temperature, 333)
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.static_temperature, 296.265, 3)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.static_temperature,  313.76513, 5)

        np.testing.assert_almost_equal(next_stage.inlet_flow_station.total_pressure, 124787.12942, 5)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.total_pressure, 159563.80095, 5)
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.static_pressure, 108924.147, 3)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.static_pressure, 129567.45266, 5)
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.density, 1.281, 3)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.density,  1.43883, 5)

        np.testing.assert_almost_equal(next_stage.inlet_flow_station.inner_radius, 0.121, 3)
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.outer_radius, 0.218, 3)
        np.testing.assert_almost_equal(next_stage.inlet_flow_station.radius, 0.1696031)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.inner_radius, 0.12612, 5)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.outer_radius, 0.21308, 5)
        np.testing.assert_almost_equal(next_stage.mid_flow_station.radius, 0.1696031)


if __name__ == '__main__':
    unittest.main()
