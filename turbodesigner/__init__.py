"""
TurboDesigner - The open-source turbomachinery designer
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("turbodesigner")
except PackageNotFoundError:
    __version__ = "0.0.0"

# Import main modules for easier access
from turbodesigner.flow_station import FlowStation
from turbodesigner.stage import Stage
from turbodesigner.turbomachinery import Turbomachinery
from turbodesigner.units import MM, DEG, BAR
from turbodesigner.visualizer import TurbomachineryVisualizer

# Make these modules available at the package level
__all__ = [
    "FlowStation",
    "Stage",
    "Turbomachinery",
    "MM",
    "DEG",
    "BAR",
    "TurbomachineryVisualizer",
]