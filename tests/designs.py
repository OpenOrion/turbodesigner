import json
import os
from turbodesigner.cli.state import TurboDesign

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def _load(name: str):
    return TurboDesign.from_file(f"{TEST_DIR}/designs/{name}.json").definition


base_design = _load("base_design")
mark1 = _load("mark1")
