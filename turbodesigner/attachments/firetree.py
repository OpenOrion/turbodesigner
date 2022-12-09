from typing import Optional
import numpy as np
from dataclasses import dataclass
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
    is_clockwise: bool = True
):
    lower_distance = lower_point - center
    upper_distance = upper_point - center
    angle1 = np.arctan2(lower_distance[1], lower_distance[0])
    angle2 = np.arctan2(upper_distance[1], upper_distance[0])

    if not is_clockwise:
        angle1 = angle1 + 2*np.pi

    angle = np.linspace(angle1, angle2, num_points, endpoint=True)
    return center + np.array([
        radius * np.cos(angle),
        radius * np.sin(angle),
    ]).T


@dataclass
class FirtreeAttachment:
    gamma: float
    "angle of upper flank line (rad)"

    beta: float
    "angle of lower flank line (rad)"

    ll: float
    "lower flank line length (m)"

    lu: float
    "upper flank line length (m)"

    Ri: float
    "inner circle radius"

    Ro: float
    "outer circle radius"

    R_dove: float
    "dove circle radius"

    max_length: float
    "max length of attachment"

    num_stages: int
    "number of stages"

    disk_radius: float
    "disk radius of attachment"


    def get_dove_arc(self, origin: np.ndarray, num_arc_points: int):
        "calculates firtree dove arc"
        dove_circle_center = np.array([self.R_dove*np.sin(self.beta), -self.R_dove*np.cos(self.beta)])
        lower_point = dove_circle_center + np.array([0,-self.R_dove])
        return get_arc(lower_point, origin, self.R_dove, dove_circle_center, num_arc_points, is_clockwise=False)

    def get_top_arc(self, start_point: np.ndarray, num_arc_points: int):
        "calculates firtree top arc"
        sector_angle = 2*np.arcsin((self.max_length/2)/self.disk_radius)
        top_arc_left_point = start_point
        top_arc_right_point = start_point + np.array([self.max_length, 0])
        top_arc_height = self.disk_radius - (self.max_length/2)/np.tan(sector_angle/2)
        disk_center = np.array([0,top_arc_left_point[1]-self.disk_radius+top_arc_height])
        return get_arc(top_arc_left_point, top_arc_right_point, self.disk_radius, disk_center, num_arc_points)


    def get_stage(self, origin: np.ndarray, num_arc_points: int):
        "calculates firtree single stage coordinates"

        # Outer Circle
        outer_circle_lower_tangent = origin + (
            np.array([self.ll*np.cos(self.beta), self.ll*np.sin(self.beta)])
        )
        outer_circle_upper_tangent = outer_circle_lower_tangent + (
            np.array([0, 2*self.Ro*np.cos(self.gamma)])
        )
        outer_circle_tanget_intersect = outer_circle_lower_tangent + (
            np.array([self.Ro*(1 - np.sin(self.gamma)**2)/np.sin(self.gamma), self.Ro*np.cos(self.gamma),])
        )
        outer_circle_center = outer_circle_lower_tangent + (
            np.array([-self.Ro*np.sin(self.gamma), self.Ro*np.cos(self.gamma)])
        )

        # Inner Circle
        inner_circle_lower_tangent = outer_circle_upper_tangent + (
            np.array([-self.lu*np.cos(self.gamma), self.lu*np.sin(self.gamma)])
        )
        inner_circle_upper_tangent = inner_circle_lower_tangent + (
            np.array([0, 2*self.Ri*np.cos(self.gamma)])
        )
        inner_circle_center = inner_circle_lower_tangent + (
            np.array([self.Ri*np.sin(self.beta), self.Ri*np.cos(self.beta)])
        )

        # Flank Lines
        yl = np.linspace(origin[1], outer_circle_lower_tangent[1], 20)
        lower_flank_line = get_line(yl, origin, outer_circle_lower_tangent)

        yu = np.linspace(outer_circle_upper_tangent[1], inner_circle_lower_tangent[1], 20)
        upper_flank_line = get_line(yu, outer_circle_tanget_intersect, outer_circle_upper_tangent)

        # Arcs
        outer_arc = get_arc(outer_circle_lower_tangent, outer_circle_upper_tangent, self.Ro, outer_circle_center, num_arc_points)
        inner_arc = get_arc(inner_circle_lower_tangent, inner_circle_upper_tangent, self.Ri, inner_circle_center, num_arc_points, is_clockwise=False)

        return np.concatenate([lower_flank_line, outer_arc, upper_flank_line, inner_arc])

    def get_coords(self, num_arc_points: int = 20):
        "calculates firtree attachment coordinates"
        origin = np.array([0, 0])
        stage = self.get_stage(origin, num_arc_points)
        attachment_left_side = stage
        # TODO: make this more efficient with Numba
        for i in range(self.num_stages):
            next_stage = stage+attachment_left_side[-1]-origin
            if i == self.num_stages - 1:
                next_stage = next_stage[:-num_arc_points]
            attachment_left_side = np.concatenate([attachment_left_side, next_stage])

        dove_arc = self.get_dove_arc(origin, num_arc_points)
        attachment_left_side = np.concatenate([dove_arc, attachment_left_side])

        # offset side to max length
        attachment_left_side = attachment_left_side + np.array([-attachment_left_side[-1][0]-self.max_length/2, 0])
        
        # attachment right side (mirrored from left)
        attachment_right_side = np.array([-1, 1]) * np.flip(attachment_left_side, axis=0)

        top_arc = self.get_top_arc(attachment_left_side[-1], num_arc_points)

        return np.concatenate([attachment_left_side, top_arc, attachment_right_side, [attachment_left_side[0]]])

    def visualize(self, num_arc_points: int = 20):
        coords = self.get_coords(num_arc_points)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=coords[:, 0],
            y=coords[:, 1],
        ))
        fig.layout.yaxis.scaleanchor = "x"
        fig.show()

