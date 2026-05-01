"""Tests for turbodesigner.exporter module - DataFrame generation."""
import unittest

import numpy as np
import pandas as pd

from tests.designs import base_design, mark1
from turbodesigner.exporter import (
    machine_properties_df,
    dataclass_list_to_df,
    stages_flow_stations_df,
    stages_blade_rows_df,
    stages_blade_rows_streams_df,
    stages_blade_rows_sub_models_dfs,
)


class MachinePropertiesDfTest(unittest.TestCase):
    """Tests for machine_properties_df()."""

    def test_returns_dataframe(self):
        df = machine_properties_df(base_design)
        self.assertIsInstance(df, pd.DataFrame)

    def test_has_columns(self):
        df = machine_properties_df(base_design)
        self.assertGreater(len(df.columns), 0)

    def test_contains_key_properties(self):
        df = machine_properties_df(base_design)
        index_str = " ".join(str(i) for i in df.index.tolist())
        # Should have entries for key computed properties
        self.assertTrue(any("temperature" in str(i).lower() for i in df.index))

    def test_mark1(self):
        df = machine_properties_df(mark1)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)


class DataclassListToDfTest(unittest.TestCase):
    """Tests for dataclass_list_to_df()."""

    def test_returns_dataframe(self):
        df = dataclass_list_to_df(base_design.stages)
        self.assertIsInstance(df, pd.DataFrame)

    def test_has_stage_columns(self):
        df = dataclass_list_to_df(base_design.stages)
        self.assertEqual(len(df.columns), 7)
        self.assertIn("Stage 1", df.columns)
        self.assertIn("Stage 7", df.columns)

    def test_mark1_stages(self):
        df = dataclass_list_to_df(mark1.stages)
        self.assertEqual(len(df.columns), 5)

    def test_has_rows(self):
        df = dataclass_list_to_df(base_design.stages)
        self.assertGreater(len(df), 0)


class StagesFlowStationsDfTest(unittest.TestCase):
    """Tests for stages_flow_stations_df()."""

    def test_returns_dataframe(self):
        df = stages_flow_stations_df(base_design)
        self.assertIsInstance(df, pd.DataFrame)

    def test_has_stage_columns(self):
        df = stages_flow_stations_df(base_design)
        self.assertGreater(len(df.columns), 0)

    def test_mark1(self):
        df = stages_flow_stations_df(mark1)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)


class StagesBladeRowsDfTest(unittest.TestCase):
    """Tests for stages_blade_rows_df()."""

    def test_returns_dataframe(self):
        df = stages_blade_rows_df(base_design)
        self.assertIsInstance(df, pd.DataFrame)

    def test_has_content(self):
        df = stages_blade_rows_df(base_design)
        self.assertGreater(len(df), 0)
        self.assertGreater(len(df.columns), 0)

    def test_mark1(self):
        df = stages_blade_rows_df(mark1)
        self.assertIsInstance(df, pd.DataFrame)


class StagesBladeRowsStreamsDfTest(unittest.TestCase):
    """Tests for stages_blade_rows_streams_df()."""

    def test_returns_dataframe(self):
        df = stages_blade_rows_streams_df(base_design)
        self.assertIsInstance(df, pd.DataFrame)

    def test_has_content(self):
        df = stages_blade_rows_streams_df(base_design)
        self.assertGreater(len(df), 0)


class StagesBladeRowsSubModelsDfsTest(unittest.TestCase):
    """Tests for stages_blade_rows_sub_models_dfs()."""

    def test_returns_dict(self):
        result = stages_blade_rows_sub_models_dfs(base_design)
        self.assertIsInstance(result, dict)

    def test_values_are_dataframes(self):
        result = stages_blade_rows_sub_models_dfs(base_design)
        for key, df in result.items():
            self.assertIsInstance(df, pd.DataFrame, f"{key} is not a DataFrame")


if __name__ == "__main__":
    unittest.main()
