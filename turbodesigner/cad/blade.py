import cadquery as cq
import numpy as np
from turbodesigner.blade.row import BladeRowExport

class BladeCadModel:
    @staticmethod
    def blade_profile(
        blade_row: BladeRowExport,
    ):
        blade_profile = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, blade_row.hub_radius))
            .polyline(blade_row.airfoils[0])
            .close()
        )

        for i in range(0, len(blade_row.radii) - 1):
            blade_profile = (
                blade_profile
                .transformed(offset=cq.Vector(0, 0, blade_row.radii[i+1]-blade_row.radii[i]))
                .polyline(blade_row.airfoils[i+1])
                .close()
            )

        path = (
            cq.Workplane("XZ")
            .moveTo(0, blade_row.hub_radius)
            .lineTo(0, blade_row.tip_radius)
        )

        blade_profile = (
            blade_profile
            .sweep(path, multisection=True, makeSolid=True)
        )

        return (
            blade_profile
            .combine()
            .translate((0, 0, -blade_row.hub_radius))
        )