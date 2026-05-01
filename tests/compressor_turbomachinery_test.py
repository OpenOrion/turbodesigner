import unittest
import numpy as np
from tests.designs import base_design
from turbodesigner.flow_station import FlowStation
from turbodesigner.stage import Stage


class CompressorDesignTest(unittest.TestCase):
    def test_flow_station_base_design(self):
        np.testing.assert_almost_equal(base_design.outlet_flow_station.total_pressure, 419150)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.static_pressure, 87908.56, 2)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.static_pressure, 383948.29, 2)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.static_temperature, 276.80039821)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.static_temperature, 441.27919465)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.density, 1.10657931)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.density, 3.03163833)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.flow_area, 0.12049144)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.physical_area, 0.12049144)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.flow_area, 0.04398062)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.physical_area, 0.044, 3)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.total_temperature, 452.47879644)
        np.testing.assert_almost_equal(base_design.overall_temperature_rise, 164.47879644)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.inner_radius, 0.11307, 5)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.inner_radius, 0.14897, 5)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.outer_radius, 0.22614, 5)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.outer_radius, 0.19024, 5)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.radius, 0.16960, 5)
        np.testing.assert_almost_equal(base_design.outlet_flow_station.radius, 0.16960, 5)
        np.testing.assert_almost_equal(base_design.inlet_flow_station.rpm, 15000)


if __name__ == '__main__':
    unittest.main()
