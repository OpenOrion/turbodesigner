import unittest
from turbodesigner.blade.row import BladeDeviation, AirfoilType
import numpy as np

class AungierDeviationTest(unittest.TestCase):

    def test_aungier_deviation(self):
        deviation = BladeDeviation(
            beta1=np.radians(70),               # rad
            beta2=np.radians(20),               # rad
            sigma=2.0,                          # dimensionless
            tbc=0.1,                            # dimensionless
            airfoil_type=AirfoilType.NACA65
        )

        metal_angles = deviation.get_metal_angles(100)

        np.testing.assert_almost_equal(np.degrees(metal_angles.kappa1), 73.9657, 4)
        np.testing.assert_almost_equal(np.degrees(metal_angles.kappa2), -0.4597, 4)


if __name__ == '__main__':
    unittest.main()
