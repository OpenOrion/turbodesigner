import unittest
import numpy as np
from turbodesigner.flow_station import FlowStation
from turbodesigner.blade.vortex.free_vortex import FreeVortex

class VelocityTriangleTest(unittest.TestCase):

    def test_velocity_triangle(self):
        inlet_flow_station = FlowStation(
            Vm=150,           # m/s
            N=15000,          # RPM
            radius=0.1696031, # m
            alpha=0,          # rad
        )

        outlet_flow_station = FlowStation(
            Vm=150,                         # m/s
            N=15000,                        # RPM
            radius=0.1696031,               # m
            alpha=np.radians(26.69005971),  # rad
        )

        # Inlet Flow Station
        np.testing.assert_almost_equal(np.degrees(inlet_flow_station.alpha), 0.0)
        np.testing.assert_almost_equal(np.degrees(inlet_flow_station.beta), -60.61884197)
        np.testing.assert_almost_equal(inlet_flow_station.Vm, 150.0)
        np.testing.assert_almost_equal(inlet_flow_station.ctheta, 0.0)
        np.testing.assert_almost_equal(inlet_flow_station.c, 150.0)
        np.testing.assert_almost_equal(inlet_flow_station.U, 266.41192649)
        np.testing.assert_almost_equal(inlet_flow_station.wtheta, -266.41192649)
        np.testing.assert_almost_equal(inlet_flow_station.w, 305.73732938)

        # Outlet Flow Station
        np.testing.assert_almost_equal(np.degrees(outlet_flow_station.alpha), 26.69005971)
        np.testing.assert_almost_equal(np.degrees(outlet_flow_station.beta), -51.85637225)
        np.testing.assert_almost_equal(outlet_flow_station.Vm, 150.0)
        np.testing.assert_almost_equal(outlet_flow_station.ctheta, 75.40953689)
        np.testing.assert_almost_equal(outlet_flow_station.c, 167.88864838)
        np.testing.assert_almost_equal(outlet_flow_station.wtheta, -191.0023896)
        np.testing.assert_almost_equal(outlet_flow_station.w, 242.86192133)

    def test_free_vortex_angles(self):
        N = 6000                 # RPM
        rm = 0.475               # m
        Um = (1/30)*np.pi*N*rm   # m/s
        cx = 136                 # m/s
        Rm=1-0.5*(0.5/0.475)**2
        ctheta1_m = 78.6 * (0.5/.475)
        ctheta2_m = 235.6 * (0.5/.475)
        psi_m = (ctheta2_m - ctheta1_m) / Um
        vortex = FreeVortex(
            Um=Um,               # m/s
            Vm=cx,               # m/s
            Rm=Rm,               # dimensionless
            psi_m=psi_m,         # dimensionless
            rm=rm                # m
        )

        ctheta1_hub = vortex.ctheta(r=0.45, is_rotating=True)
        ctheta2_hub = vortex.ctheta(r=0.45, is_rotating=False)
        alpha1_hub = vortex.alpha(r=0.45, is_rotating=True)
        alpha2_hub = vortex.alpha(r=0.45, is_rotating=False)
        
        ctheta1_tip = vortex.ctheta(r=0.5, is_rotating=True)
        ctheta2_tip = vortex.ctheta(r=0.5, is_rotating=False)
        alpha1_tip = vortex.alpha(r=0.5, is_rotating=True)
        alpha2_tip = vortex.alpha(r=0.5, is_rotating=False)

        # Hub
        np.testing.assert_almost_equal(ctheta1_hub, 87.31, 2)
        np.testing.assert_almost_equal(ctheta2_hub, 261.755, 3)
        np.testing.assert_almost_equal(np.degrees(alpha1_hub), 32.70, 2)
        np.testing.assert_almost_equal(np.degrees(alpha2_hub), 62.54, 2)

        # Tip
        np.testing.assert_almost_equal(ctheta1_tip, 78.57, 2)
        np.testing.assert_almost_equal(ctheta2_tip, 235.58, 2)
        np.testing.assert_almost_equal(np.degrees(alpha1_tip), 30.02, 2)
        np.testing.assert_almost_equal(np.degrees(alpha2_tip), 60.00, 2)


if __name__ == '__main__':
    unittest.main()