"""
TurboDesigner - The open-source turbomachinery designer
"""

__version__ = "0.1.0"

# Import main modules for easier access
from turbodesigner.flow_station import FlowStation
from turbodesigner.stage import Stage
from turbodesigner.turbomachinery import Turbomachinery
from turbodesigner.units import MM, DEG, BAR
from turbodesigner.visualizer import TurbomachineryVisualizer
from turbodesigner.exporter import TurbomachineryExporter

# Make these modules available at the package level
__all__ = [
    "FlowStation",
    "Stage",
    "Turbomachinery",
    "MM",
    "DEG",
    "BAR",
    "TurbomachineryVisualizer",
    "TurbomachineryExporter",
]