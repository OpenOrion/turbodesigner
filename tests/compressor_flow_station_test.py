import unittest
import numpy as np
from turbodesigner.flow_station import FlowStation
from turbodesigner.stage import Stage


class CompressorFlowStationTest(unittest.TestCase):
    def test_stage_flow_station(self):
        inlet_flow_station = FlowStation(
            gamma=1.4,
            gas_constant=287,
            total_temperature=450,
            total_pressure=2.80E5,
            mass_flow_rate=2.2,
            meridional_velocity=263.95,
            flow_angle=0,
            rpm=36000,
            radius=0.08,
        )

        np.testing.assert_almost_equal(inlet_flow_station.relative_flow_angle, np.radians(-48.808), 3)
        np.testing.assert_almost_equal(inlet_flow_station.blade_velocity, 301.593, 3)
        np.testing.assert_almost_equal(inlet_flow_station.absolute_velocity, 263.95, 3)
        np.testing.assert_almost_equal(inlet_flow_station.critical_velocity, 388.169, 3)
        np.testing.assert_almost_equal(inlet_flow_station.relative_total_temperature, 495.275, 3)
        np.testing.assert_almost_equal(inlet_flow_station.relative_total_pressure, 391631.736, 3)
        np.testing.assert_almost_equal(inlet_flow_station.tangential_velocity, 0.00, 3)

        mid_flow_station = FlowStation(
            gamma=1.4,
            gas_constant=287,
            total_temperature=504.6,
            total_pressure=3.60E5,
            mass_flow_rate=2.2,
            meridional_velocity=263.95,
            flow_angle=0.593,
            rpm=36000,
            radius=0.08,
        )

        np.testing.assert_almost_equal(mid_flow_station.relative_tangential_velocity, -123.715, 3)
        np.testing.assert_almost_equal(mid_flow_station.relative_total_temperature, 496.469, 3)
        np.testing.assert_almost_equal(mid_flow_station.relative_total_pressure, 340102.039, 3)


    def test_velocity_triangle(self):
        inlet_flow_station = FlowStation(
            meridional_velocity=150,
            rpm=15000,
            radius=0.1696031,
            flow_angle=0,
        )

        outlet_flow_station = FlowStation(
            meridional_velocity=150,
            rpm=15000,
            radius=0.1696031,
            flow_angle=np.radians(26.69005971),
        )

        # Inlet Flow Station
        np.testing.assert_almost_equal(np.degrees(inlet_flow_station.flow_angle), 0.0)
        np.testing.assert_almost_equal(np.degrees(inlet_flow_station.relative_flow_angle), -60.61884197)
        np.testing.assert_almost_equal(inlet_flow_station.meridional_velocity, 150.0)
        np.testing.assert_almost_equal(inlet_flow_station.tangential_velocity, 0.0)
        np.testing.assert_almost_equal(inlet_flow_station.absolute_velocity, 150.0)
        np.testing.assert_almost_equal(inlet_flow_station.blade_velocity, 266.41192649)
        np.testing.assert_almost_equal(inlet_flow_station.relative_tangential_velocity, -266.41192649)
        np.testing.assert_almost_equal(inlet_flow_station.relative_velocity, 305.73732938)

        # Outlet Flow Station
        np.testing.assert_almost_equal(np.degrees(outlet_flow_station.flow_angle), 26.69005971)
        np.testing.assert_almost_equal(np.degrees(outlet_flow_station.relative_flow_angle), -51.85637225)
        np.testing.assert_almost_equal(outlet_flow_station.meridional_velocity, 150.0)
        np.testing.assert_almost_equal(outlet_flow_station.tangential_velocity, 75.40953689)
        np.testing.assert_almost_equal(outlet_flow_station.absolute_velocity, 167.88864838)
        np.testing.assert_almost_equal(outlet_flow_station.relative_tangential_velocity, -191.0023896)
        np.testing.assert_almost_equal(outlet_flow_station.relative_velocity, 242.86192133)


if __name__ == '__main__':
    unittest.main()
