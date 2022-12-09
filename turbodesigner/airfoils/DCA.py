from dataclasses import dataclass
import plotly.graph_objects as go
import numpy as np
from scipy import stats

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

    def __post_init__(self):
        self.theta_mag = np.abs(self.theta)

    def get_camber_line(self, num_points = 20):
        """coordinates of camber line (length)

            num_points: int
                number of points
        """
        # radius of curvature (length)
        Rc = (self.c/2) * (1/(np.sin(self.theta/2)))
        
        # camber line y-coordinate origin of radius (length)
        yc0 = -Rc * np.cos(self.theta/2)

        # horizontal position of camber or chord line (length)
        xc = np.linspace(-self.c/2, self.c/2, num_points, endpoint=True)
        
        # vertical position of camber or chord line (length)
        yc = yc0 + np.sqrt(Rc**2 - xc**2) * np.sign(self.theta)

        return np.array([xc,yc]).T

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

        # x values weighted in center
        distribution = stats.norm(loc=0, scale=0.20)
        bounds = distribution.cdf([-self.c/2, self.c/2])
        percentage_points = np.linspace(*bounds, num=num_points)
        x = distribution.ppf(percentage_points)

        # camberline coordinate at mid coord (length)
        ym = (self.c/2)*np.tan(self.theta_mag/4)
        
        # radius of circular arc (length)
        d = ym + (tb / 2) - r0*np.sin(self.theta_mag/2)
        R = (d**2 - (r0**2) + ((self.c/2) - r0 * np.cos(self.theta_mag/2))**2)/(2*(d-r0))
        
        # origin of circular arc (length)
        y0 = ym + (tb/2) - R

        y = np.sign(self.theta) * (y0 + np.sqrt(R**2 - x**2))

        if is_lower and np.abs(y[0]) > self.tb/2:
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
        # Circles
        left_circle = self.get_circle(is_left=True, num_points=num_circle_points)
        right_circle = self.get_circle(is_left=False, num_points=num_circle_points)

        # Arcs
        upper_arc = self.get_arc(is_lower=False, num_points=num_arc_points)
        lower_arc = self.get_arc(is_lower=True, num_points=num_arc_points)
        left_circle_start = np.array([left_circle[0]])

        upper_cond = np.where(np.logical_and(upper_arc[:,0] > left_circle[0,0], upper_arc[:,0] < right_circle[-1,0]))
        lower_cond = np.where(np.logical_and(lower_arc[:,0] > left_circle[-1,0], lower_arc[:,0] < right_circle[0,0]))
        
        return np.concatenate(
            [
                left_circle, 
                lower_arc[lower_cond],
                right_circle, 
                np.flip(upper_arc[upper_cond], axis=0), 
                left_circle_start
            ]
        )

    def visualize(
        self,
        num_arc_points: int = 20, 
        num_circle_points: int = 10
    ):
        fig = go.Figure()
        xy_c = self.get_camber_line(num_arc_points)
        xy = self.get_coords(num_arc_points, num_circle_points)
        
        fig.add_trace(go.Scatter(
            x=xy_c[:, 0],
            y=xy_c[:, 1],
        ))

        fig.add_trace(go.Scatter(
            x=xy[:, 0],
            y=xy[:, 1],
            fill="toself"
        ))

        fig.layout.yaxis.scaleanchor="x"
        fig.show()
