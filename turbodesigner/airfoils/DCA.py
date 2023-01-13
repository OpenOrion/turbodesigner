from dataclasses import dataclass
from functools import cached_property
from typing import Optional, Union
import plotly.graph_objects as go
import numpy as np
from turbodesigner.airfoils.common import get_staggered_coords

@dataclass
class DCAAirfoil:
    c: float
    "chord length (length)"

    theta: float
    "camber angle (rad)"

    r0: float
    "double circular arc airfoil nose radius (length)"

    tb: float
    "max thickness (length)"

    xi: float = 0
    "stagger angle (rad)"

    arc_weight: float = 0.8
    "percentage of how much of x coordinates to load for arc"

    def __post_init__(self):
        if self.theta == 0:
            self.theta = 1E-5
        self.theta_mag = np.abs(self.theta)


    def get_camber_line(self, xc:Optional[Union[float, np.ndarray]] = None, is_staggered: bool = True, is_centered: bool = True,  num_points = 20):
        """coordinates of camber line (length)

            num_points: int
                number of points
        """
        # horizontal position of camber or chord line (length)
        if xc is None:
            xc = np.linspace(-self.c/2, self.c/2, num_points, endpoint=True)
        y_sign = np.sign(self.theta)
        # radius of curvature (length)
        Rc = (self.c/2) * (1/(np.sin(self.theta/2)))
        
        # camber line y-coordinate origin of radius (length)
        yc0 = -Rc * np.cos(self.theta/2)
        
        # vertical position of camber of chord line (length)
        yc = yc0 + np.sqrt(Rc**2 - xc**2) * y_sign

        camber_line = np.array([xc,yc]).T

        if is_centered:
            camber_line = camber_line - np.array([0,yc0 + np.sqrt(Rc**2) * y_sign])

        if is_staggered:
            camber_line = get_staggered_coords(camber_line, self.xi)
        return camber_line

    def get_circle(self, is_left: bool, num_points: int):
        """coordinates of circle for DCA airfoil (length)
        
            is_left: bool
                whether it is the left circle of DCA airfoil

            num_points: int
                number of points
        """

        x_sign = -1 if is_left else 1
        x_center = x_sign*(self.c/2 - self.r0*np.cos(self.theta_mag/2))
        y_center = self.r0 * np.sin(self.theta_mag/2)

        center_to_end_distance = (x_sign*self.c/2) - x_center
        angle_offset = np.pi - np.arccos(center_to_end_distance/self.r0) + np.pi/2
        angle = np.linspace(0, np.pi, num_points, endpoint=True) + angle_offset

        x = self.r0 * np.cos(angle) + x_center
        y = (self.r0 * np.sin(angle) + y_center) * np.sign(self.theta)

        return np.array([x,y]).T


    def get_arc(self, is_lower = False, num_points=20):
        """y-coordinates of chord line (length)
        
            is_lower: bool = False
                whether arc is lower
        
        """
        # negate tb and r0 if this a lower arc
        input_sign = -1 if is_lower else 1
        r0 = input_sign*self.r0
        tb = input_sign*self.tb

        x = np.linspace(-self.c*self.arc_weight/2, self.c*self.arc_weight/2, num=num_points)

        # camberline coordinate at mid coord (length)
        ym = (self.c/2)*np.tan(self.theta_mag/4)
        
        # radius of circular arc (length)
        d = ym + (tb / 2) - r0*np.sin(self.theta_mag/2)
        R = (d**2 - (r0**2) + ((self.c/2) - r0 * np.cos(self.theta_mag/2))**2)/(2*(d-r0))
        
        # origin of circular arc (length)
        y0 = ym + (tb/2) - R

        y = np.sign(self.theta) * (y0 + np.sqrt(R**2 - x**2))

        if is_lower and np.abs(y[0]) > self.tb*2:
            y = -np.sign(self.theta) * np.ones(num_points) * self.r0

        return np.array([x,y]).T
    
    def get_coords(
        self, 
        num_arc_points: int = 20, 
        num_circle_points: int = 10
    ):
        """double circular arc airfoil coordinates

            num_arc_points: int
                number of arc points

            num_circle_points: int
                number of circle points

        """
        # Info: x coordinates are [:,0] and y coordinates are [:,1]

        # Circles
        left_circle = self.get_circle(is_left=True, num_points=num_circle_points)
        right_circle = self.get_circle(is_left=False, num_points=num_circle_points)

        # Arcs
        upper_arc = self.get_arc(is_lower=False, num_points=num_arc_points)
        lower_arc = self.get_arc(is_lower=True, num_points=num_arc_points)
        left_circle_start = np.array([left_circle[0]])

        upper_cond = np.where(np.logical_and(upper_arc[:,0] > left_circle[0,0], upper_arc[:,0] < right_circle[-1,0]))
        lower_cond = np.where(np.logical_and(lower_arc[:,0] > left_circle[-1,0], lower_arc[:,0] < right_circle[0,0]))
        
        center = self.get_camber_line(0, is_staggered=False, is_centered=False)
        airfoil = np.concatenate(
            [
                left_circle, 
                lower_arc[lower_cond],
                right_circle, 
                np.flip(upper_arc[upper_cond], axis=0), 
                left_circle_start
            ]
        ) - center

        return get_staggered_coords(airfoil, self.xi)

    def visualize(
        self,
        fig=go.Figure(),
        show=True,
        num_arc_points: int = 20, 
        num_circle_points: int = 10
    ):
        camber_xy = self.get_camber_line(num_points=num_arc_points)
        fig.add_trace(go.Scatter(
            x=camber_xy[:, 0],
            y=camber_xy[:, 1],
        ))

        xy = self.get_coords(num_arc_points, num_circle_points)
        fig.add_trace(go.Scatter(
            x=xy[:, 0],
            y=xy[:, 1],
            fill="toself"
        ))

        fig.layout.yaxis.scaleanchor="x"  # type: ignore
        if show:
            fig.show()
