import numpy as np
from turbodesigner.turbomachinery import Turbomachinery
import plotly.graph_objects as go
from IPython.display import Image, display


class TurbomachineryVisualizer:
    @staticmethod
    def visualize_annulus(turbomachinery: Turbomachinery, is_interactive=False):
        rotors = [
            np.array([
                [(stage.stage_number-1.), stage.rotor.rt],
                [(stage.stage_number-1.)+0.5, stage.stator.rt],
                [(stage.stage_number-1.)+0.5, stage.stator.rh],
                [(stage.stage_number-1.), stage.rotor.rh],
                [(stage.stage_number-1.), stage.rotor.rt],
            ])
            for stage in turbomachinery.stages
        ]

        stators = [
            np.array([
                [(stage.stage_number-1.)+0.5, stage.stator.rt],
                [stage.stage_number, (stage.next_stage.rotor if stage.next_stage else stage.stator).rt],
                [stage.stage_number, (stage.next_stage.rotor if stage.next_stage else stage.stator).rh],
                [(stage.stage_number-1.)+0.5, stage.stator.rh],
                [(stage.stage_number-1.)+0.5, stage.stator.rt],
            ])
            for stage in turbomachinery.stages
        ]


        fig = go.Figure(
            layout=go.Layout(
                title=go.layout.Title(text="Annulus"),
            )
        )
        for (i, rotor) in enumerate(rotors):
            fig.add_trace(go.Scatter(
                x=rotor[:, 0],
                y=rotor[:, 1],
                fill="toself",
                fillcolor="red",
                line_color="red",
                legendgroup="rotor",
                legendgrouptitle_text="Rotor",
                name=f"Rotor {i+1}"
            ))

        for (i, stator) in enumerate(stators):
            fig.add_trace(go.Scatter(
                x=stator[:, 0],
                y=stator[:, 1],
                fill="toself",
                fillcolor="blue",
                line_color="blue",
                legendgroup="stator",
                legendgrouptitle_text="Stator",
                name=f"Stator {i+1}"
            ))

        

        if is_interactive:
            fig.show()
        else:
            image = Image(fig.to_image(format="png", width=800, height=500, scale=2))
            display(image)