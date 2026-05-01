from functools import cached_property
from typing import Union
import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class Vortex(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    mean_blade_velocity: float = Field(description="Mean blade velocity (m/s)")

    meridional_velocity: float = Field(description="Meridional flow velocity (m/s)")

    mean_reaction: float = Field(description="Mean reaction rate (dimensionless)")

    mean_loading_coefficient: float = Field(description="Mean loading coefficient (dimensionless)")

    mean_radius: float = Field(description="Mean radius (m)")

    @cached_property
    def mean_flow_coefficient(self) -> float:
        """Mean flow coefficient (dimensionless)"""
        return self.meridional_velocity / self.mean_blade_velocity

    def ctheta(self, r: Union[float, np.ndarray], is_rotating: bool):
        """Absolute tangential velocity (m/s)"""
        return np.nan

    def alpha(self, r: Union[float, np.ndarray], is_rotating: bool):
        """Absolute flow angle (rad)"""
        return np.arctan(self.ctheta(r, is_rotating) / self.meridional_velocity)