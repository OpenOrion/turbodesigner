import unittest
import numpy as np
from tests.designs import base_design

class CompressorDesignTest(unittest.TestCase):
    def test_flow_angles(self):
        alpha2 = base_design.stages[0].stator.flow_station.alpha
        beta1 = base_design.stages[0].rotor.flow_station.beta
        beta2 = base_design.stages[0].stator.flow_station.beta

        np.testing.assert_allclose(np.degrees(alpha2), np.array([33.89769494, 25.41478326, 20.1796603 ]))
        np.testing.assert_allclose(np.degrees(beta1), np.array([-50.78398542, -60.99475883, -67.28474591]))
        np.testing.assert_allclose(np.degrees(beta2), np.array([-30.28750731, -52.45117333, -62.59349512]))