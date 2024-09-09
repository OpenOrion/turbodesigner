# import unittest
# from turbodesigner.blade.deviation.johnsen_bullock import JohnsenBullockBladeDeviation, AirfoilType
# import numpy as np


# class AungierDeviationTest(unittest.TestCase):

#     def test_aungier_deviation(self):
#         deviation = JohnsenBullockBladeDeviation(
#             beta1=np.radians(70),               # rad
#             beta2=np.radians(20),               # rad
#             sigma=2.0,                          # dimensionless
#             tbc=0.1,                            # dimensionless
#             airfoil_type=AirfoilType.NACA65
#         )

#         metal_angles = deviation.get_metal_angles(100)


#         np.testing.assert_almost_equal(np.degrees(metal_angles.kappa1), 73.9657, 4)
#         np.testing.assert_almost_equal(np.degrees(metal_angles.kappa2), -0.4597, 4)



#     def test_aungier_zero_camber_sigma_2(self):
#         deviation = JohnsenBullockBladeDeviation(
#             beta1=np.radians(70),               # rad
#             beta2=np.radians(70),               # rad
#             sigma=2.0,                          # dimensionless
#             tbc=0.1,                            # dimensionless
#             airfoil_type=AirfoilType.NACA65
#         )

#         metal_angles = deviation.get_metal_angles(1)
#         np.testing.assert_almost_equal(np.degrees(metal_angles.i), 10.1975, 4)
#         np.testing.assert_almost_equal(np.degrees(metal_angles.delta), 4.7296, 4)

#     def test_aungier_zero_camber_sigma_1(self):
#         deviation = JohnsenBullockBladeDeviation(
#             beta1=np.radians(70),               # rad
#             beta2=np.radians(70),               # rad
#             sigma=1.0,                          # dimensionless
#             tbc=0.1,                            # dimensionless
#             airfoil_type=AirfoilType.NACA65
#         )

#         metal_angles = deviation.get_metal_angles(1)
#         np.testing.assert_almost_equal(np.degrees(metal_angles.i), 5.0897, 4)
#         np.testing.assert_almost_equal(np.degrees(metal_angles.delta), 2.5691, 4)



# if __name__ == '__main__':
#     unittest.main()
