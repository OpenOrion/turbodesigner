from functools import cached_property
from typing import Optional
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
import plotly.graph_objects as go


def get_line(
    y: np.ndarray,
    point1: np.ndarray,
    point2: np.ndarray,
    y_int: Optional[int] = None
):
    x2, y2 = point2[0], point2[1]
    x1, y1 = point1[0], point1[1]
    m = (y2 - y1) / (x2 - x1)
    b = y2 - m*x2 if y_int is None else 0
    x = (y-b)/m
    return np.array([x, y]).T


def get_arc(
    lower_point: np.ndarray,
    upper_point: np.ndarray,
    radius: float,
    center: np.ndarray,
    num_points: int,
    is_clockwise: bool = True,
    endpoint: bool = True
):
    lower_distance = lower_point - center
    upper_distance = upper_point - center
    angle1 = np.arctan2(lower_distance[1], lower_distance[0])
    angle2 = np.arctan2(upper_distance[1], upper_distance[0])

    if not is_clockwise:
        angle1 = angle1 + 2*np.pi

    angle = np.linspace(angle1, angle2, num_points, endpoint=endpoint)
    return center + np.array([
        radius * np.cos(angle),
        radius * np.sin(angle),
    ]).T


class FirtreeAttachment(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    gamma: float = Field(description="Angle of upper flank line (rad)")
    beta: float = Field(description="Angle of lower flank line (rad)")
    ll: float = Field(description="Lower flank line length (m)")
    lu: float = Field(description="Upper flank line length (m)")
    Ri: float = Field(description="Inner circle radius (m)")
    Ro: float = Field(description="Outer circle radius (m)")
    R_dove: float = Field(description="Dove circle radius (m)")
    max_length: float = Field(description="Max length of attachment (m)")
    num_stages: int = Field(description="Number of stages")
    disk_radius: float = Field(description="Disk radius (m)")
    tolerance: float = Field(description="Attachment side tolerance (m)")
    include_top_arc: bool = Field(default=True, description="Whether to include top arc")
    num_arc_points: int = Field(default=20, description="Number of arc points")

    def model_post_init(self, __context):
        self._origin = np.array([0, 0])

        # Outer Circle
        self._outer_circle_lower_tangent = self._origin + (
            np.array([self.ll*np.cos(self.beta), self.ll*np.sin(self.beta)])
        )
        self._outer_circle_upper_tangent = self._outer_circle_lower_tangent + (
            np.array([0, 2*self.Ro*np.cos(self.gamma)])
        )
        self._outer_circle_tanget_intersect = self._outer_circle_lower_tangent + (
            np.array([self.Ro*(1 - np.sin(self.gamma)**2)/np.sin(self.gamma), self.Ro*np.cos(self.gamma)])
        )
        self._outer_circle_center = self._outer_circle_lower_tangent + (
            np.array([-self.Ro*np.sin(self.gamma), self.Ro*np.cos(self.gamma)])
        )

        # Inner Circle
        self._inner_circle_lower_tangent = self._outer_circle_upper_tangent + (
            np.array([-self.lu*np.cos(self.gamma), self.lu*np.sin(self.gamma)])
        )
        self._inner_circle_upper_tangent = self._inner_circle_lower_tangent + (
            np.array([0, 2*self.Ri*np.cos(self.gamma)])
        )
        self._inner_circle_center = self._inner_circle_lower_tangent + (
            np.array([self.Ri*np.sin(self.beta), self.Ri*np.cos(self.beta)])
        )

        # Dove
        self._dove_circle_center = np.array([self.R_dove*np.sin(self.beta), -self.R_dove*np.cos(self.beta)])
        self._dove_lower_point = self._dove_circle_center + np.array([0, -self.R_dove])

    @cached_property
    def dove_arc(self):
        """Firtree dove arc coordinates"""
        return get_arc(self._dove_lower_point, self._origin, self.R_dove, self._dove_circle_center, self.num_arc_points, is_clockwise=False)

    def get_top_shape(self, include_tolerance: bool):
        """Firtree top arc or line segment"""
        max_length = self.max_length + self.tolerance if include_tolerance else self.max_length
        top_arc_left_point = self.left_side[-1]
        top_arc_right_point = top_arc_left_point + np.array([max_length, 0])

        if self.include_top_arc:
            sector_angle = 2*np.arcsin((max_length/2)/self.disk_radius)
            top_arc_height = self.disk_radius - (max_length/2)/np.tan(sector_angle/2)
            disk_center = np.array([0, top_arc_left_point[1]-self.disk_radius+top_arc_height])
            return get_arc(top_arc_left_point, top_arc_right_point, self.disk_radius, disk_center, self.num_arc_points)

        return np.concatenate([[top_arc_left_point], [top_arc_right_point]])

    def get_stage(self, end_stage: bool = False):
        """Single firtree stage coordinates"""
        yl = np.linspace(self._origin[1], self._outer_circle_lower_tangent[1], 2, endpoint=False)
        lower_flank_line = get_line(yl, self._origin, self._outer_circle_lower_tangent)

        yu = np.linspace(self._outer_circle_upper_tangent[1], self._inner_circle_lower_tangent[1], 2, endpoint=False)
        upper_flank_line = get_line(yu, self._outer_circle_tanget_intersect, self._outer_circle_upper_tangent)

        outer_arc = get_arc(self._outer_circle_lower_tangent, self._outer_circle_upper_tangent, self.Ro, self._outer_circle_center, self.num_arc_points, endpoint=False)
        inner_arc = get_arc(self._inner_circle_lower_tangent, self._inner_circle_upper_tangent, self.Ri, self._inner_circle_center, self.num_arc_points, is_clockwise=False)

        stage_elements = [lower_flank_line, outer_arc, upper_flank_line]
        if not end_stage:
            stage_elements.append(inner_arc)

        return np.concatenate(stage_elements)

    @cached_property
    def left_side(self) -> np.ndarray:
        """Firtree attachment left side coordinates"""
        stage = self.get_stage()
        attachment_stage_side: Optional[np.ndarray] = None
        assert self.num_stages > 0, "num stages must greater than 0"
        for i in range(self.num_stages):
            next_stage = stage
            if attachment_stage_side is not None:
                attachment_stage_side = np.concatenate([
                    attachment_stage_side[:-1],
                    next_stage + attachment_stage_side[-1]
                ])
            else:
                attachment_stage_side = next_stage

        assert attachment_stage_side is not None
        attachment_center_offset = np.array([-attachment_stage_side[-1][0]-self.max_length/2, 0])
        return np.concatenate([self.dove_arc[:-1], attachment_stage_side]) + attachment_center_offset

    def get_coords(self, include_tolerance: bool):
        """Firtree attachment coordinates"""
        top_arc = self.get_top_shape(include_tolerance)
        left_side = self.left_side + np.array([-self.tolerance/2, 0]) if include_tolerance else self.left_side
        attachment_right_side = np.flip(left_side, axis=0) * np.array([-1, 1])
        attachment = np.concatenate([left_side[:-1], top_arc[:-1], attachment_right_side, [left_side[0]]])
        return attachment + np.array([0, -np.max(attachment[:, 1])])

    @cached_property
    def coords(self):
        return self.get_coords(include_tolerance=False)

    @cached_property
    def coords_with_tolerance(self):
        return self.get_coords(include_tolerance=True)

    @cached_property
    def height(self):
        return np.max(self.coords[:, 1]) - np.min(self.coords[:, 1])

    @cached_property
    def bottom_width(self):
        return np.abs(self.left_side[0][0]) * 2

    def visualize(self):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.coords[:, 0],
            y=self.coords[:, 1],
        ))
        fig.layout.yaxis.scaleanchor = "x"
        fig.show()
