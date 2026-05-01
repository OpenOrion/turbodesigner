import unittest
from turbodesigner.blade.metal_angle_methods.johnsen_bullock import JohnsenBullockMetalAngleMethod
from turbodesigner.blade.metal_angles import MetalAngles
from turbodesigner.airfoils import AirfoilType
import numpy as np


class AungierDeviationTest(unittest.TestCase):

    def test_aungier_deviation(self):
        method = JohnsenBullockMetalAngleMethod(
            inlet_flow_angle=np.radians(70),
            outlet_flow_angle=np.radians(20),
            solidity=2.0,
            max_thickness_to_chord=0.1,
            airfoil_type=AirfoilType.NACA65
        )

        offset = method.get_metal_angle_offset(100)
        metal_angles = MetalAngles(
            inlet_flow_angle=np.radians(70),
            outlet_flow_angle=np.radians(20),
            incidence=offset.i,
            deviation=offset.delta,
        )

        np.testing.assert_almost_equal(np.degrees(metal_angles.inlet_metal_angle), 73.9657, 4)
        np.testing.assert_almost_equal(np.degrees(metal_angles.outlet_metal_angle), -0.4597, 4)



    def test_aungier_zero_camber_sigma_2(self):
        method = JohnsenBullockMetalAngleMethod(
            inlet_flow_angle=np.radians(70),
            outlet_flow_angle=np.radians(70),
            solidity=2.0,
            max_thickness_to_chord=0.1,
            airfoil_type=AirfoilType.NACA65
        )

        offset = method.get_metal_angle_offset(1)
        np.testing.assert_almost_equal(np.degrees(offset.i), 10.1975, 4)
        np.testing.assert_almost_equal(np.degrees(offset.delta), 4.7296, 4)

    def test_aungier_zero_camber_sigma_1(self):
        method = JohnsenBullockMetalAngleMethod(
            inlet_flow_angle=np.radians(70),
            outlet_flow_angle=np.radians(70),
            solidity=1.0,
            max_thickness_to_chord=0.1,
            airfoil_type=AirfoilType.NACA65
        )

        offset = method.get_metal_angle_offset(1)
        np.testing.assert_almost_equal(np.degrees(offset.i), 5.0897, 4)
        np.testing.assert_almost_equal(np.degrees(offset.delta), 2.5691, 4)



if __name__ == '__main__':
    unittest.main()
