from dataclasses import dataclass
from functools import cached_property
from typing import Optional
import cadquery as cq
from turbodesigner.cad.common import ExtendedWorkplane, FastenerPredicter
from turbodesigner.cad.blade import BladeCadModel, BladeCadModelSpecification
from turbodesigner.stage import StageExport
from turbodesigner.turbomachinery import TurbomachineryExport


@dataclass
class ShaftCadModelSpecification:
    is_simple: bool = False
    "whether to include attachment or fuse into shaft (bool)"

    shaft_transition_to_total_height: float = 0.25
    "casing transition height to total stage height (dimensionless)"

    stage_connect_length_to_heatset_thickness: float = 2.00
    "shaft stage connect to hub radius (dimensionless)"

    stage_connect_height_to_screw_head_diameter: float = 1.75
    "shaft stage connect to disk height (dimensionless)"

    stage_connect_padding_to_attachment_height: float = 1.25
    "shaft stage connect padding to attachment height (dimensionless)"

    stage_connect_heatset_diameter_to_disk_height: float = 0.05
    "shaft stage connect heatset diameter to disk height (dimensionless)"

    stage_connect_screw_quantity: int = 4
    "shaft stage connect screw quantity (dimensionless)"

    stage_connect_clearance: float = 0.5
    "shaft stage connect circular clearance (mm)"

@dataclass
class ShaftCadModel:
    stage: StageExport
    "turbomachinery stage"

    next_stage: Optional[StageExport] = None
    "next turbomachinery stage"

    spec: ShaftCadModelSpecification = ShaftCadModelSpecification()
    "shaft cad model specification"

    def __post_init__(self):
        self.transition_height = self.stage.stage_height * self.spec.shaft_transition_to_total_height

        self.stage_connect_heatset = FastenerPredicter.predict_heatset(
            target_diameter=self.stage.rotor.disk_height*self.spec.stage_connect_heatset_diameter_to_disk_height,
        )
        self.stage_connect_length = self.stage_connect_heatset.nut_thickness * self.spec.stage_connect_length_to_heatset_thickness

        self.blade_cad_model = BladeCadModel(
            self.stage.rotor,
            spec=BladeCadModelSpecification(
                not self.spec.is_simple,
                screw_length_padding=self.stage_connect_length
            )
        )

        # TODO: Just used to get head diameter, length doesn't matter
        self.stage_connect_screw = FastenerPredicter.predict_screw(target_diameter=self.stage_connect_heatset.thread_diameter)

        self.stage_connect_height = self.stage_connect_screw.head_diameter * self.spec.stage_connect_height_to_screw_head_diameter
        stage_connect_padding = self.stage.rotor.attachment_height * self.spec.stage_connect_padding_to_attachment_height
        self.stage_connect_outer_radius = self.stage.rotor.hub_radius-stage_connect_padding
        self.stage_connect_inner_radius = self.stage_connect_outer_radius-self.stage_connect_length

        if self.next_stage:
            self.next_stage_shaft_cad_model = ShaftCadModel(self.next_stage, spec=self.spec)
            self.next_stage_stage_connect_screw = FastenerPredicter.predict_screw(
                target_diameter=self.next_stage_shaft_cad_model.stage_connect_heatset.thread_diameter,
                target_length=self.next_stage_shaft_cad_model.stage_connect_heatset.nut_thickness + (self.stage.stator.hub_radius - self.next_stage_shaft_cad_model.stage_connect_outer_radius)
            )

    @cached_property
    def shaft_stage_sector(self):
        sector_angle = 360 / self.stage.rotor.number_of_blades
        sector_cut_profile = (
            cq.Workplane('XZ')
            .transformed(rotate=(0, sector_angle/2, 0))
            .rect(self.stage.stator.hub_radius, self.stage.stage_height*2, centered=False)
            .revolve(sector_angle*(self.stage.rotor.number_of_blades-1), (0, 0, 0), (0, 1, 0))
        )

        shaft_profile = self.shaft_stage_assembly.objects["Stage Shaft"].obj
        assert shaft_profile is not None and isinstance(shaft_profile, cq.Workplane)
        shaft_sector_profile = (
            shaft_profile
            .cut(sector_cut_profile)
        )

        return shaft_sector_profile

    @cached_property
    def shaft_stage_assembly(self):
        base_assembly = cq.Assembly()
        blade_assembly = cq.Assembly()
        fastener_assembly = cq.Assembly()

        shaft_profile = (
            # Stator Disk
            ExtendedWorkplane("XY")
            .circle(self.stage.stator.hub_radius)
            .extrude(self.stage.stator.disk_height)

            # Transition Disk
            .faces(">Z")
            .workplane()
            .truncated_cone(
                start_radius=self.stage.stator.hub_radius,
                end_radius=self.stage.rotor.hub_radius,
                height=self.transition_height
            )

            # Rotor Disk
            .faces(">Z")
            .workplane()
            .circle(self.stage.rotor.hub_radius)
            .extrude(self.stage.rotor.disk_height)
        )

        if not self.spec.is_simple:
            shaft_profile = (
                shaft_profile

                # Cut Attachments - TODO: make this operation faster
                .faces(">Z")
                .workplane()
                .polarArray(1.0001*self.stage.rotor.hub_radius, 0, 360, self.stage.rotor.number_of_blades)
                .eachpoint(
                    lambda loc: (
                        cq.Workplane("XY")
                        .polyline(self.stage.rotor.attachment_with_tolerance)  # type: ignore
                        .close()
                        .rotate((0, 0, 0), (0, 0, 1), 270)
                    ).val().located(loc), True)  # type: ignore
                .cutBlind(-self.stage.rotor.disk_height)

                # Shaft Male Connect
                .faces(">Z")
                .workplane()
                .circle(self.stage_connect_outer_radius)
                .extrude(self.stage_connect_height)

                # Shaft Connect Hole
                .faces(">Z")
                .workplane()
                .circle(self.stage_connect_inner_radius*1.001)
                .cutThruAll()

                # Blade Lock Screws
                .faces(">Z")
                .workplane(offset=-self.stage_connect_height-self.blade_cad_model.lock_screw.head_diameter*1.5)
                .polarArray(self.stage_connect_inner_radius, 0, 360, self.stage.rotor.number_of_blades)
                .mutatePoints(lambda loc: loc * cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), -90))
                .clearanceHole(self.blade_cad_model.lock_screw, fit="Loose", baseAssembly=fastener_assembly)

                # Shaft Connect Heatsets
                .faces(">Z")
                .workplane(offset=-self.stage_connect_height/2)
                .polarArray(self.stage_connect_outer_radius, 0, 360, self.spec.stage_connect_screw_quantity)
                .mutatePoints(lambda loc: loc * cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 90))
                .insertHole(self.stage_connect_heatset, fit="Loose", baseAssembly=fastener_assembly, depth=self.stage_connect_heatset.nut_thickness)
            )
            if self.next_stage_shaft_cad_model:
                shaft_profile = (
                    # Next Shaft Female Connect
                    shaft_profile
                    .faces("<Z")
                    .workplane()
                    .circle(self.next_stage_shaft_cad_model.stage_connect_outer_radius + self.spec.stage_connect_clearance)
                    .cutBlind(-self.next_stage_shaft_cad_model.stage_connect_height)
                    
                    # Next Shaft Connect Screws
                    .faces("<Z")
                    .workplane(offset=-self.next_stage_shaft_cad_model.stage_connect_height/2)
                    .polarArray(self.next_stage_shaft_cad_model.stage.rotor.hub_radius, 0, 360, self.spec.stage_connect_screw_quantity)
                    .mutatePoints(lambda loc: loc * cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 90))
                    .clearanceHole(self.next_stage_stage_connect_screw, fit="Loose", baseAssembly=fastener_assembly)
                )
            

        
        blade_vertical_offset = self.stage.stator.disk_height+self.transition_height+self.stage.rotor.disk_height/2
        blade_assembly_locs = (
            ExtendedWorkplane("XY")
            .polarArray(self.stage.rotor.hub_radius, 0, 360, self.stage.rotor.number_of_blades)
            .mutatePoints(lambda loc: loc * cq.Location(cq.Vector(0, 0, blade_vertical_offset), cq.Vector(0, 1, 0), 90))
            .vals()
        )

        for (i, blade_assembly_loc) in enumerate(blade_assembly_locs):
            assert isinstance(blade_assembly_loc, cq.Location)
            blade_assembly.add(self.blade_cad_model.blade_assembly, loc=blade_assembly_loc, name=f"Blade {i+1}")
        
        base_assembly.add(shaft_profile, name=f"Stage Shaft")
        base_assembly.add(blade_assembly, name="Blades")
        base_assembly.add(fastener_assembly, name="Fasteners")
        return base_assembly

    @staticmethod
    def shaft_assembly(turbomachinery: TurbomachineryExport, spec: ShaftCadModelSpecification=ShaftCadModelSpecification()):
        assembly = cq.Assembly()
        stage_height_offset = 0

        for i in range(0, len(turbomachinery.stages)):
            current_stage = turbomachinery.stages[i]
            next_stage = turbomachinery.stages[i+1] if i+1 < len(turbomachinery.stages) else current_stage

            stage_height_offset -= current_stage.stage_height * (1+spec.shaft_transition_to_total_height)
            shaft_cad_model = ShaftCadModel(current_stage, next_stage, spec)
            assembly.add(shaft_cad_model.shaft_stage_assembly, loc=cq.Location(cq.Vector(0, 0, stage_height_offset)), name=f"Stage {current_stage.stage_number}")

        return assembly
