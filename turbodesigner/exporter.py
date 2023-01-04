from typing import Callable, Dict
import numpy as np
import pandas as pd
from turbodesigner.stage import Stage
from turbodesigner.turbomachinery import Turbomachinery
from turbodesigner.units import DEG, BAR

def get_hub_mean_tip_table(turbomachinery: Turbomachinery, on_stage: Callable[[Stage], Dict]):
    table = {
        "Hub": dict(),
        "Mean": dict(),
        "Tip": dict()
    }
    
    for stage in turbomachinery.stages:
        representation = on_stage(stage)
        for (key, value) in representation.items():
            table["Hub"][(f"Stage {stage.stage_number}", key)] = value[0] if isinstance(value, np.ndarray) else value
            table["Mean"][(f"Stage {stage.stage_number}", key)] = np.median(value) if isinstance(value, np.ndarray) else value
            table["Tip"][(f"Stage {stage.stage_number}", key)] = value[-1] if isinstance(value, np.ndarray) else value

    return pd.DataFrame(table)


def get_rotor_stator_table(turbomachinery: Turbomachinery, on_stage: Callable[[Stage], Dict]):
    table = dict()    
    for stage in turbomachinery.stages:
        representation = on_stage(stage)
        for (key, value) in representation.items():
            if key not in table:
                table[key] = dict()
            table[key][(f"Stage {stage.stage_number}", "Rotor")] = value["Rotor"]
            table[key][(f"Stage {stage.stage_number}", "Stator")] = value["Stator"]
    return pd.DataFrame(table)


class TurbomachineryExporter:
    @staticmethod
    def turbomachinery_properties(turbomachinery: Turbomachinery):
        properties = {
            "gamma (dimensionless)": turbomachinery.gamma,
            "cx (m/s)": turbomachinery.cx,
            "N (rpm)": turbomachinery.N,
            "Rs (J/(kgK))": turbomachinery.Rs,
            "mdot (kg/s)": turbomachinery.mdot,
            "PR (dimensionless)": turbomachinery.PR,
            "P01 (Pa)": turbomachinery.P01,
            "T01 (K)": turbomachinery.T01,
            "eta_isen (dimensionless)": turbomachinery.eta_isen,
            "eta_poly (dimensionless)": turbomachinery.eta_poly,
            "N_stg": turbomachinery.N_stg,                             
            "B_in (dimensionless)":  turbomachinery.B_in,                     
            "B_out (dimensionless)": turbomachinery.B_out,
            "ht (dimensionless)": turbomachinery.ht,
        }
        return pd.DataFrame.from_dict(properties, orient='index')

    @staticmethod
    def stage_properties(turbomachinery: Turbomachinery):
        return pd.DataFrame(
            [
                {
                    "Stage": stage.stage_number,
                    "Delta_T0 (K)": stage.Delta_T0,
                    "R (dimensionless)": stage.R,
                    "PR (dimensionless)": stage.PR,
                    "phi (dimensionless)": stage.phi,
                    "psi (dimensionless)": stage.psi
                }
                for stage in turbomachinery.stages
            ],
        )

    @staticmethod
    def stage_fluid_properties(turbomachinery: Turbomachinery):
        return pd.DataFrame(
            [
                {
                    "Stage": stage.stage_number,
                    "T01 (K)": stage.inlet_flow_station.T0,
                    "T1 (K)": stage.inlet_flow_station.T,
                    "P01 (bar)": stage.inlet_flow_station.P0 * BAR,
                    "P1 (bar)": stage.inlet_flow_station.P * BAR,
                    "rho1 (kg/m^3)": stage.inlet_flow_station.rho,
                    "T02 (K)": stage.mid_flow_station.T0,
                    "T2 (K)": stage.mid_flow_station.T,
                    "P02 (bar)": stage.mid_flow_station.P0 * BAR,
                    "P2 (bar)": stage.mid_flow_station.P * BAR,
                    "rho2 (kg/m^3)": stage.mid_flow_station.rho,
                }
                for stage in turbomachinery.stages
            ]
        )

    @staticmethod
    def annulus(turbomachinery: Turbomachinery):
        return get_rotor_stator_table(
            turbomachinery,
            lambda stage : {
                "rh (m)": {
                    "Rotor": stage.rotor.rh,
                    "Stator": stage.stator.rh,
                },
                "rt (m)": {
                    "Rotor": stage.rotor.rt,
                    "Stator": stage.stator.rt,
                },
                "rm (m)": {
                    "Rotor": stage.rotor.rm,
                    "Stator": stage.stator.rm,
                }
            }
        )


    @staticmethod
    def velocity_triangle(turbomachinery: Turbomachinery):
        return get_hub_mean_tip_table(
            turbomachinery,
            lambda stage : {
                    "cx (m/s)": stage.rotor.flow_station.Vm,
                    "U (m/s)": stage.rotor.flow_station.U,
                    "ctheta1 (m/s)": stage.rotor.flow_station.ctheta,
                    "c1 (m/s)": stage.rotor.flow_station.c,
                    "wtheta1 (m/s)": stage.rotor.flow_station.wtheta,
                    "w1 (m/s)": stage.rotor.flow_station.w,
                    "beta1 (deg)": stage.rotor.flow_station.beta * DEG,
                    "alpha1 (deg)": stage.rotor.flow_station.alpha * DEG,
                    "ctheta2 (m/s)": stage.rotor.flow_station.ctheta,
                    "c2 (m/s)": stage.rotor.flow_station.c,
                    "wtheta2 (m/s)": stage.rotor.flow_station.wtheta,
                    "w2 (m/s)": stage.rotor.flow_station.w,
                    "beta2 (deg)": stage.rotor.flow_station.beta * DEG,
                    "alpha2 (deg)": stage.rotor.flow_station.alpha * DEG,
            }
        )

    @staticmethod
    def blade_angles(turbomachinery: Turbomachinery):
        return get_hub_mean_tip_table(
            turbomachinery,
            lambda stage : {
                    "kappa1 (deg)": stage.rotor.metal_angles.kappa1 * DEG,
                    "kappa2 (deg)": stage.rotor.metal_angles.kappa2 * DEG,
                    "theta (deg)": stage.rotor.metal_angles.theta * DEG,
                    "xi (deg)": stage.rotor.metal_angles.xi * DEG,
            }
        )

    @staticmethod
    def blade_properties(turbomachinery: Turbomachinery):
        return get_rotor_stator_table(
            turbomachinery,
            lambda stage : {
                "sc (dimensionless)": {
                    "Rotor": stage.rotor.sc,
                    "Stator": stage.stator.sc,
                },
                "AR (dimensionless)": {
                    "Rotor": stage.rotor.AR,
                    "Stator": stage.stator.AR,
                },
                "tbc (dimensionless)": {
                    "Rotor": stage.rotor.tbc,
                    "Stator": stage.stator.tbc,
                },
                "sigma (dimensionless)": {
                    "Rotor": stage.rotor.sigma,
                    "Stator": stage.stator.sigma,
                },
                "c (m)": {
                    "Rotor": stage.rotor.c,
                    "Stator": stage.stator.c,
                },
                "h (m)": {
                    "Rotor": stage.rotor.h,
                    "Stator": stage.stator.h,
                }
            }
        )


