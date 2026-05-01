"""Tests for turbodesigner.cli.state module - TurboDesign and workspace management."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from turbodesigner.cli.state import (
    TurboDesign,
    ensure_workspace,
    get_workspace_dir,
    get_config,
    set_config,
    get_active_design_name,
    set_active_design,
    clear_active_design,
    list_designs,
    get_design_path,
    resolve_design,
    load_design_export,
    save_design_export,
    load_design,
    save_design,
    save_design_from_json,
    delete_design,
    get_output_dir,
    load_shaft_spec,
    load_casing_spec,
    load_blade_spec,
    save_cad_spec,
    get_cad_spec_summary,
)
from turbodesigner.turbomachinery import Turbomachinery


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DESIGN_PATH = os.path.join(TEST_DIR, "designs", "base_design.json")
MARK1_PATH = os.path.join(TEST_DIR, "designs", "mark1.json")


class TurboDesignFromFileTest(unittest.TestCase):
    """Tests for TurboDesign.from_file()."""

    def test_from_file_loads_base_design(self):
        td = TurboDesign.from_file(BASE_DESIGN_PATH)
        self.assertIsInstance(td, TurboDesign)
        self.assertIsInstance(td.definition, Turbomachinery)
        self.assertEqual(td.machine_type, "axial")
        self.assertEqual(td.configuration, "compressor")

    def test_from_file_loads_mark1(self):
        td = TurboDesign.from_file(MARK1_PATH)
        self.assertEqual(td.definition.num_stages, 5)
        self.assertAlmostEqual(td.definition.pressure_ratio, 3.0)

    def test_from_file_definition_has_stages(self):
        td = TurboDesign.from_file(BASE_DESIGN_PATH)
        self.assertEqual(td.definition.num_stages, 7)
        self.assertEqual(len(td.definition.stages), 7)

    def test_from_file_flat_format(self):
        """Test that a flat JSON (just turbomachinery fields) is handled."""
        td = TurboDesign.from_file(BASE_DESIGN_PATH)
        flat_data = td.definition.model_dump()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(flat_data, f)
            f.flush()
            td2 = TurboDesign.from_file(f.name)

        os.unlink(f.name)
        self.assertEqual(td2.definition.num_stages, td.definition.num_stages)
        self.assertAlmostEqual(td2.definition.pressure_ratio, td.definition.pressure_ratio)

    def test_from_file_nonexistent_raises(self):
        with self.assertRaises(FileNotFoundError):
            TurboDesign.from_file("/nonexistent/path.json")

    def test_from_file_invalid_json_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            f.flush()
        with self.assertRaises(json.JSONDecodeError):
            TurboDesign.from_file(f.name)
        os.unlink(f.name)

    def test_from_file_cad_defaults(self):
        td = TurboDesign.from_file(BASE_DESIGN_PATH)
        self.assertIsNotNone(td.cad)
        self.assertIsNotNone(td.cad.shaft)
        self.assertIsNotNone(td.cad.casing)
        self.assertIsNotNone(td.cad.blade)


class WorkspaceManagementTest(unittest.TestCase):
    """Tests for workspace state management functions."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TURBODESIGNER_WORKSPACE")
        os.environ["TURBODESIGNER_WORKSPACE"] = self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self.original_env is not None:
            os.environ["TURBODESIGNER_WORKSPACE"] = self.original_env
        else:
            os.environ.pop("TURBODESIGNER_WORKSPACE", None)

    def test_ensure_workspace_creates_structure(self):
        ws = ensure_workspace()
        self.assertTrue(ws.exists())
        self.assertTrue((ws / "designs").exists())
        self.assertTrue((ws / "cache").exists())
        self.assertTrue((ws / "config.json").exists())

    def test_get_config_default(self):
        ensure_workspace()
        config = get_config()
        self.assertIsNone(config["active_design"])

    def test_set_and_get_config(self):
        ensure_workspace()
        set_config({"active_design": "test_design", "custom": True})
        config = get_config()
        self.assertEqual(config["active_design"], "test_design")
        self.assertTrue(config["custom"])

    def test_active_design_lifecycle(self):
        ensure_workspace()
        self.assertIsNone(get_active_design_name())

        set_active_design("mydesign")
        self.assertEqual(get_active_design_name(), "mydesign")

        clear_active_design()
        self.assertIsNone(get_active_design_name())

    def test_save_and_load_design(self):
        ensure_workspace()
        design_path = save_design("test1", BASE_DESIGN_PATH)
        self.assertTrue(os.path.exists(design_path))

        name, tm = load_design("test1")
        self.assertEqual(name, "test1")
        self.assertIsInstance(tm, Turbomachinery)
        self.assertEqual(tm.num_stages, 7)

    def test_save_design_from_json(self):
        ensure_workspace()
        with open(BASE_DESIGN_PATH) as f:
            json_str = f.read()
        design_path = save_design_from_json("json_test", json_str)
        self.assertTrue(os.path.exists(design_path))

        name, tm = load_design("json_test")
        self.assertEqual(name, "json_test")
        self.assertEqual(tm.num_stages, 7)

    def test_list_designs_empty(self):
        ensure_workspace()
        self.assertEqual(list_designs(), [])

    def test_list_designs_after_save(self):
        ensure_workspace()
        save_design("alpha", BASE_DESIGN_PATH)
        save_design("beta", MARK1_PATH)
        designs = list_designs()
        self.assertIn("alpha", designs)
        self.assertIn("beta", designs)
        self.assertEqual(designs, sorted(designs))

    def test_get_design_path_exists(self):
        ensure_workspace()
        save_design("pathtest", BASE_DESIGN_PATH)
        path = get_design_path("pathtest")
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())

    def test_get_design_path_nonexistent(self):
        ensure_workspace()
        self.assertIsNone(get_design_path("nonexistent"))

    def test_resolve_design_with_name(self):
        ensure_workspace()
        save_design("resolvetest", BASE_DESIGN_PATH)
        name, path = resolve_design("resolvetest")
        self.assertEqual(name, "resolvetest")
        self.assertTrue(path.exists())

    def test_resolve_design_uses_active(self):
        ensure_workspace()
        save_design("active_resolve", BASE_DESIGN_PATH)
        set_active_design("active_resolve")
        name, path = resolve_design(None)
        self.assertEqual(name, "active_resolve")

    def test_resolve_design_no_active_raises(self):
        ensure_workspace()
        with self.assertRaises(ValueError):
            resolve_design(None)

    def test_resolve_design_nonexistent_raises(self):
        ensure_workspace()
        set_active_design("ghost")
        with self.assertRaises(ValueError):
            resolve_design("ghost")

    def test_delete_design(self):
        ensure_workspace()
        save_design("todelete", BASE_DESIGN_PATH)
        self.assertIn("todelete", list_designs())

        result = delete_design("todelete")
        self.assertTrue(result)
        self.assertNotIn("todelete", list_designs())

    def test_delete_design_clears_active(self):
        ensure_workspace()
        save_design("active_del", BASE_DESIGN_PATH)
        set_active_design("active_del")
        delete_design("active_del")
        self.assertIsNone(get_active_design_name())

    def test_delete_nonexistent_returns_false(self):
        ensure_workspace()
        self.assertFalse(delete_design("nope"))

    def test_get_output_dir(self):
        ensure_workspace()
        save_design("outputtest", BASE_DESIGN_PATH)
        out = get_output_dir("outputtest")
        self.assertTrue(out.exists())
        self.assertTrue(out.is_dir())

    def test_load_design_export(self):
        ensure_workspace()
        save_design("exporttest", BASE_DESIGN_PATH)
        export = load_design_export("exporttest")
        self.assertIsInstance(export, TurboDesign)
        self.assertEqual(export.definition.num_stages, 7)

    def test_save_design_export_roundtrip(self):
        ensure_workspace()
        td = TurboDesign.from_file(BASE_DESIGN_PATH)
        save_design_export("roundtrip", td)
        loaded = load_design_export("roundtrip")
        self.assertEqual(loaded.definition.num_stages, td.definition.num_stages)
        self.assertAlmostEqual(loaded.definition.pressure_ratio, td.definition.pressure_ratio)

    def test_cad_spec_load_defaults(self):
        ensure_workspace()
        save_design("cadtest", BASE_DESIGN_PATH)
        shaft = load_shaft_spec("cadtest")
        casing = load_casing_spec("cadtest")
        blade = load_blade_spec("cadtest")
        self.assertIsNotNone(shaft)
        self.assertIsNotNone(casing)
        self.assertIsNotNone(blade)

    def test_cad_spec_save_and_load(self):
        ensure_workspace()
        save_design("cadspec_rw", BASE_DESIGN_PATH)
        shaft = load_shaft_spec("cadspec_rw")
        shaft.stage_connect_screw_quantity = 8
        save_cad_spec("cadspec_rw", "shaft", shaft)
        reloaded = load_shaft_spec("cadspec_rw")
        self.assertEqual(reloaded.stage_connect_screw_quantity, 8)

    def test_get_cad_spec_summary(self):
        ensure_workspace()
        save_design("summarytest", BASE_DESIGN_PATH)
        summary = get_cad_spec_summary("summarytest")
        self.assertIn("shaft", summary)
        self.assertIn("casing", summary)
        self.assertIn("blade", summary)


if __name__ == "__main__":
    unittest.main()
