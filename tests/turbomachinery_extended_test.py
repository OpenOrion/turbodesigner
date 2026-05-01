"""Tests for Turbomachinery computed properties and methods not covered by existing tests."""
import json
import os
import tempfile
import unittest

import numpy as np

from tests.designs import base_design, mark1
from turbodesigner.turbomachinery import Turbomachinery, TurbomachineryCadExport
from turbodesigner.cli.state import TurboDesign


class TurbomachineryComputedPropertiesTest(unittest.TestCase):
    """Tests for Turbomachinery cached/computed properties."""

    def test_polytropic_efficiency(self):
        eta_p = base_design.polytropic_efficiency
        self.assertGreater(eta_p, 0.8)
        self.assertLess(eta_p, 1.0)

    def test_outlet_total_temperature(self):
        T_out = base_design.outlet_total_temperature
        self.assertGreater(T_out, base_design.inlet_total_temperature)

    def test_outlet_total_pressure(self):
        P_out = base_design.outlet_total_pressure
        self.assertAlmostEqual(P_out, base_design.inlet_total_pressure * base_design.pressure_ratio)

    def test_overall_temperature_rise(self):
        dT = base_design.overall_temperature_rise
        self.assertAlmostEqual(
            dT,
            base_design.outlet_total_temperature - base_design.inlet_total_temperature,
        )

    def test_stages_count(self):
        self.assertEqual(len(base_design.stages), base_design.num_stages)
        self.assertEqual(len(mark1.stages), mark1.num_stages)

    def test_stages_temperature_rise_sums(self):
        """Sum of stage temperature rises should approximate overall."""
        total_rise = sum(s.temperature_rise for s in base_design.stages)
        self.assertAlmostEqual(total_rise, base_design.overall_temperature_rise, delta=1.0)

    def test_inlet_flow_station(self):
        fs = base_design.inlet_flow_station
        self.assertAlmostEqual(fs.total_pressure, base_design.inlet_total_pressure)
        self.assertAlmostEqual(fs.total_temperature, base_design.inlet_total_temperature)

    def test_outlet_flow_station(self):
        fs = base_design.outlet_flow_station
        self.assertAlmostEqual(fs.total_pressure, base_design.outlet_total_pressure)

    def test_mark1_polytropic_efficiency(self):
        eta_p = mark1.polytropic_efficiency
        self.assertGreater(eta_p, 0.8)
        self.assertLess(eta_p, 1.0)


class TurbomachineryFromDictTest(unittest.TestCase):
    """Tests for Turbomachinery.from_dict()."""

    def test_from_dict_roundtrip(self):
        data = base_design.model_dump()
        tm = Turbomachinery.from_dict(data)
        self.assertEqual(tm.num_stages, base_design.num_stages)
        self.assertAlmostEqual(tm.pressure_ratio, base_design.pressure_ratio)

    def test_from_dict_mark1(self):
        data = mark1.model_dump()
        tm = Turbomachinery.from_dict(data)
        self.assertEqual(tm.num_stages, 5)


class TurbomachineryFromFileTest(unittest.TestCase):
    """Tests for Turbomachinery.from_file()."""

    def test_from_file_base_design(self):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        tm = Turbomachinery.from_file(os.path.join(test_dir, "designs", "base_design.json"))
        self.assertEqual(tm.num_stages, 7)

    def test_from_file_mark1(self):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        tm = Turbomachinery.from_file(os.path.join(test_dir, "designs", "mark1.json"))
        self.assertEqual(tm.num_stages, 5)

    def test_from_file_flat_json(self):
        """from_file should handle flat JSON (no wrapping object)."""
        data = base_design.model_dump()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
        tm = Turbomachinery.from_file(f.name)
        os.unlink(f.name)
        self.assertEqual(tm.num_stages, 7)


class TurbomachineryCadExportTest(unittest.TestCase):
    """Tests for to_cad_export()."""

    def test_to_cad_export_returns_correct_type(self):
        export = base_design.to_cad_export()
        self.assertIsInstance(export, TurbomachineryCadExport)

    def test_to_cad_export_has_all_stages(self):
        export = base_design.to_cad_export()
        self.assertEqual(len(export.stages), base_design.num_stages)

    def test_to_cad_export_mark1(self):
        export = mark1.to_cad_export()
        self.assertEqual(len(export.stages), 5)


class TurbomachineryStagePropertiesTest(unittest.TestCase):
    """Tests for Stage computed properties not covered elsewhere."""

    def test_stage_enthalpy_rise(self):
        for stage in base_design.stages:
            h_rise = stage.enthalpy_rise
            self.assertGreater(h_rise, 0)

    def test_stage_flow_coefficient(self):
        for stage in base_design.stages:
            phi = stage.flow_coefficient
            self.assertGreater(phi, 0)
            self.assertLess(phi, 2.0)

    def test_stage_loading_coefficient(self):
        for stage in base_design.stages:
            psi = stage.loading_coefficient
            self.assertGreater(psi, 0)

    def test_stage_pressure_ratio(self):
        for stage in base_design.stages:
            pr = stage.pressure_ratio
            self.assertGreater(pr, 1.0)

    def test_stage_temperature_ratio(self):
        for stage in base_design.stages:
            tr = stage.temperature_ratio
            self.assertGreater(tr, 1.0)

    def test_stage_has_rotor_and_stator(self):
        for stage in base_design.stages:
            self.assertIsNotNone(stage.rotor)
            self.assertIsNotNone(stage.stator)

    def test_stage_rotor_is_rotating(self):
        for stage in base_design.stages:
            self.assertTrue(stage.rotor.is_rotating)
            self.assertFalse(stage.stator.is_rotating)

    def test_stage_to_cad_export(self):
        export = base_design.stages[0].to_cad_export()
        self.assertIsNotNone(export)
        self.assertIsNotNone(export.rotor)
        self.assertIsNotNone(export.stator)


class FlowStationAdditionalTest(unittest.TestCase):
    """Tests for FlowStation properties not covered by existing tests."""

    def test_mach_number(self):
        fs = base_design.inlet_flow_station
        mach = fs.mach_number
        self.assertGreater(mach, 0)
        self.assertLess(mach, 1.0)  # subsonic compressor inlet

    def test_dynamic_pressure(self):
        fs = base_design.inlet_flow_station
        q = fs.dynamic_pressure
        self.assertGreater(q, 0)

    def test_physical_area(self):
        fs = base_design.inlet_flow_station
        self.assertGreater(fs.physical_area, 0)

    def test_flow_area(self):
        fs = base_design.inlet_flow_station
        self.assertGreater(fs.flow_area, 0)

    def test_inner_outer_radius(self):
        fs = base_design.inlet_flow_station
        self.assertGreater(fs.outer_radius, fs.inner_radius)
        self.assertGreater(fs.inner_radius, 0)

    def test_radius_is_mean(self):
        fs = base_design.inlet_flow_station
        mean = (fs.inner_radius + fs.outer_radius) / 2
        self.assertAlmostEqual(fs.radius, mean, places=5)

    def test_static_temperature_less_than_total(self):
        fs = base_design.inlet_flow_station
        self.assertLess(fs.static_temperature, fs.total_temperature)

    def test_static_pressure_less_than_total(self):
        fs = base_design.inlet_flow_station
        self.assertLess(fs.static_pressure, fs.total_pressure)


if __name__ == "__main__":
    unittest.main()
