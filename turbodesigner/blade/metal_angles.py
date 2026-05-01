from functools import cached_property
from typing import Union
import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class MetalAngles(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    inlet_flow_angle: Union[float, np.ndarray] = Field(description="Blade inlet flow angle (rad)")

    outlet_flow_angle: Union[float, np.ndarray] = Field(description="Blade outlet flow angle (rad)")

    incidence: Union[float, np.ndarray] = Field(description="Blade incidence angle (rad)")

    deviation: Union[float, np.ndarray] = Field(description="Blade deviation angle (rad)")

    @cached_property
    def inlet_metal_angle(self) -> np.ndarray:
        """Inlet metal angle (rad)"""
        return np.asarray(self.inlet_flow_angle - self.incidence)

    @cached_property
    def outlet_metal_angle(self) -> np.ndarray:
        """Outlet metal angle (rad)"""
        return np.asarray(self.outlet_flow_angle - self.deviation)

    @cached_property
    def camber_angle(self) -> np.ndarray:
        """Camber angle (rad)"""
        return np.asarray(self.inlet_metal_angle - self.outlet_metal_angle)

    @cached_property
    def stagger_angle(self) -> np.ndarray:
        """Stagger angle (rad)"""
        return np.asarray((self.inlet_metal_angle + self.outlet_metal_angle) / 2)