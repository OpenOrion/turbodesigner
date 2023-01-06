import os
from turbodesigner.turbomachinery import Turbomachinery

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
base_design = Turbomachinery.from_file(f"{TEST_DIR}/designs/base_design.json")
mark1 = Turbomachinery.from_file(f"{TEST_DIR}/designs/mark1.json")
