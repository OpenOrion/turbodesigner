from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Optional
import multiprocessing as mp
import cadquery as cq
from pydantic import BaseModel, Field
from turbodesigner.cad.common import CadColors, ExtendedWorkplane, FastenerPredicter, HeatSetDims, ScrewDims, colored_assembly
from turbodesigner.cad.blade import BladeCadModel, BladeCadModelSpecification
from turbodesigner.stage import StageCadExport
from turbodesigner.turbomachinery import TurbomachineryCadExport


class ShaftCadModelSpecification(BaseModel):
    stage_connect_length_to_heatset_thickness: float = Field(default=2.0, description="Shaft stage connect to hub radius ratio")
    stage_connect_height_to_screw_head_diameter: float = Field(default=1.75, description="Shaft stage connect to disk height ratio")
    stage_connect_padding_to_attachment_height: float = Field(default=1.25, description="Shaft stage connect padding to attachment height ratio")
    stage_connect_heatset_diameter_to_disk_height: float = Field(default=0.05, description="Shaft stage connect heatset diameter to disk height ratio")
    stage_connect_screw_quantity: int = Field(default=4, description="Number of screws per shaft stage connection")
    stage_connect_clearance: float = Field(default=0.5, description="Shaft stage connect circular clearance (mm)")


@dataclass
class ShaftCadModel:
    stage: StageCadExport
    "turbomachinery stage"

    next_stage: Optional[StageCadExport] = None
    "next turbomachinery stage"

    spec: ShaftCadModelSpecification = field(default_factory=ShaftCadModelSpecification)
    "shaft cad model specification"

    is_complex: bool = False
    "whether to include fastener geometry"

    def __post_init__(self):
        # Use fast dimension lookups (no 3D geometry) for scalar calculations
        self._stage_connect_heatset_dims = FastenerPredicter.predict_heatset_dims(
            target_diameter=self.stage.rotor.disk_height*self.spec.stage_connect_heatset_diameter_to_disk_height,
        )
        self.stage_connect_length = self._stage_connect_heatset_dims.nut_thickness * self.spec.stage_connect_length_to_heatset_thickness

        self.blade_cad_model = BladeCadModel(
            self.stage.rotor,
            spec=BladeCadModelSpecification(
                screw_length_padding=self.stage_connect_length
            ),
            is_complex=self.is_complex,
        )

        screw_dims = FastenerPredicter.predict_screw_dims(target_diameter=self._stage_connect_heatset_dims.thread_diameter)

        self.stage_connect_height = screw_dims.head_diameter * self.spec.stage_connect_height_to_screw_head_diameter
        stage_connect_padding = self.stage.rotor.attachment_height * self.spec.stage_connect_padding_to_attachment_height
        self.stage_connect_outer_radius = self.stage.rotor.hub_radius-stage_connect_padding
        self.stage_connect_inner_radius = self.stage_connect_outer_radius-self.stage_connect_length

        if self.next_stage:
            self.next_stage_shaft_cad_model: Optional[ShaftCadModel] = ShaftCadModel(self.next_stage, spec=self.spec)
            # Only need dims for the next stage connect screw in __post_init__
            next_heatset_dims = self.next_stage_shaft_cad_model._stage_connect_heatset_dims
            self._next_stage_screw_dims = FastenerPredicter.predict_screw_dims(
                target_diameter=next_heatset_dims.thread_diameter,
                target_length=next_heatset_dims.nut_thickness + (self.stage.stator.hub_radius - self.next_stage_shaft_cad_model.stage_connect_outer_radius)
            )
        else:
            self.next_stage_shaft_cad_model = None
            self._next_stage_screw_dims = None

    @cached_property
    def stage_connect_heatset(self):
        return FastenerPredicter.predict_heatset(
            target_diameter=self.stage.rotor.disk_height*self.spec.stage_connect_heatset_diameter_to_disk_height,
        )

    @cached_property
    def stage_connect_screw(self):
        return FastenerPredicter.predict_screw(target_diameter=self._stage_connect_heatset_dims.thread_diameter)

    @cached_property
    def next_stage_stage_connect_screw(self):
        assert self.next_stage_shaft_cad_model is not None
        next_heatset_dims = self.next_stage_shaft_cad_model._stage_connect_heatset_dims
        return FastenerPredicter.predict_screw(
            target_diameter=next_heatset_dims.thread_diameter,
            target_length=next_heatset_dims.nut_thickness + (self.stage.stator.hub_radius - self.next_stage_shaft_cad_model.stage_connect_outer_radius)
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
        fastener_assembly = colored_assembly(CadColors.FASTENER)

        stage_gap_start_radius = self.next_stage.rotor.hub_radius if self.next_stage else self.stage.rotor.hub_radius

        shaft_profile = (
            ExtendedWorkplane("XY")
            # Stage Gap Transition
            .truncated_cone(
                start_radius=stage_gap_start_radius,
                end_radius=self.stage.stator.hub_radius,
                height=self.stage.stage_gap
            )

            # Stator Disk
            .faces(">Z")
            .workplane()
            .circle(self.stage.stator.hub_radius)
            .extrude(self.stage.stator.disk_height)

            # Row Gap Transition Disk
            .faces(">Z")
            .workplane()
            .truncated_cone(
                start_radius=self.stage.stator.hub_radius,
                end_radius=self.stage.rotor.hub_radius,
                height=self.stage.row_gap
            )

            # Rotor Disk
            .faces(">Z")
            .workplane()
            .circle(self.stage.rotor.hub_radius)
            .extrude(self.stage.rotor.disk_height)
        )

        if self.is_complex:
            shaft_profile = (
                shaft_profile

                # Tag rotor disk top while geometry is still simple
                .faces(">Z")
                .workplane()
                .tag("rotor_top")

                # Shaft Male Connect
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
            # Cut Attachments LAST using spline (no face selection needed after)
            shaft_profile = (
                shaft_profile
                .workplaneFromTagged("rotor_top")
                .polarArray(1.0001*self.stage.rotor.hub_radius, 0, 360, self.stage.rotor.number_of_blades)
                .eachpoint(
                    lambda loc: (
                        cq.Workplane("XY")
                        .spline(self.stage.rotor.attachment_with_tolerance[:-1].tolist())  # type: ignore
                        .close()
                        .rotate((0, 0, 0), (0, 0, 1), 270)
                    ).val().located(loc), True)  # type: ignore
                .cutBlind(-self.stage.rotor.disk_height)
            )

        blade_vertical_offset = self.stage.stage_gap+self.stage.stator.disk_height+self.stage.row_gap+self.stage.rotor.disk_height/2
        blade_assembly_locs = (
            ExtendedWorkplane("XY")
            .polarArray(self.stage.rotor.hub_radius, 0, 360, self.stage.rotor.number_of_blades)
            .mutatePoints(lambda loc: loc * cq.Location(cq.Vector(0, 0, blade_vertical_offset), cq.Vector(0, 1, 0), 90))
            .vals()
        )

        for (i, blade_assembly_loc) in enumerate(blade_assembly_locs):
            assert isinstance(blade_assembly_loc, cq.Location)
            blade_assembly.add(self.blade_cad_model.blade_assembly, loc=blade_assembly_loc, name=f"Blade {i+1}")

        base_assembly.add(shaft_profile, name=f"Stage Shaft", color=CadColors.SHAFT)
        base_assembly.add(blade_assembly, name="Blades")
        base_assembly.add(fastener_assembly, name="Fasteners")
        return base_assembly

    @staticmethod
    def build_assembly(stage: StageCadExport, next_stage: Optional[StageCadExport], spec: ShaftCadModelSpecification = ShaftCadModelSpecification(), output_dir: Optional[Path] = None, visualize: bool = False, accumulate: bool = False, is_complex: bool = False):
        """Build a single shaft stage assembly.

        Args:
            stage: Stage CAD export data
            next_stage: Next stage CAD export data (for female connect)
            spec: Shaft CAD model specification
            output_dir: Directory for STEP export (exports if provided)
            visualize: Send result to jupyter_cadquery viewer

        Returns:
            cq.Assembly for this stage
        """
        model = ShaftCadModel(stage, next_stage, spec, is_complex=is_complex)
        assembly = model.shaft_stage_assembly

        if output_dir:
            step_path = str(output_dir / f"shaft-stage-{stage.stage_number}.step")
            assembly.export(step_path)

        if visualize:
            from jupyter_cadquery.viewer.client import show
            from turbodesigner.cad.cache import get_tessellation_cache, save_tessellation_cache
            show(assembly, name=f"shaft-stage-{stage.stage_number}", accumulate=accumulate, reset_camera=not accumulate, cache=get_tessellation_cache())
            save_tessellation_cache()

        return assembly

    @staticmethod
    def build_all(turbomachinery: TurbomachineryCadExport, spec: ShaftCadModelSpecification = ShaftCadModelSpecification(), output_dir: Optional[Path] = None, visualize: bool = False, is_complex: bool = False):
        """Build all shaft stages in parallel subprocesses and export STEP files.

        Each stage is built in a subprocess. If visualize=True, each subprocess
        sends to the viewer as soon as it finishes (lazy/streaming).

        Args:
            turbomachinery: Full turbomachinery CAD export
            spec: Shaft CAD model specification
            output_dir: Directory for STEP exports (required)
            visualize: Send each stage to jupyter_cadquery viewer as it completes

        Returns:
            list[str]: Paths to exported STEP files
        """
        stage_data = []
        z_offset = 0.0
        for i in range(len(turbomachinery.stages)):
            stage = turbomachinery.stages[i]
            next_stage = turbomachinery.stages[i + 1] if i + 1 < len(turbomachinery.stages) else None
            stage_height = stage.stage_gap + stage.stator.disk_height + stage.row_gap + stage.rotor.disk_height
            z_offset -= stage_height
            step_path = str(output_dir / f"shaft-stage-{stage.stage_number}.step") if output_dir else None
            stage_data.append((i, stage, next_stage, step_path, z_offset))

        if visualize:
            from jupyter_cadquery.viewer.client import clear_viewer
            clear_viewer()

        ctx = mp.get_context("spawn")
        processes = []
        for i, stage, next_stage, step_path, z_off in stage_data:
            p = ctx.Process(target=_build_shaft_worker, args=(i, stage, next_stage, spec, step_path, visualize, z_off, is_complex))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        if visualize:
            from jupyter_cadquery.viewer.client import flush_viewer
            flush_viewer()

        step_paths = [sp for _, _, _, sp, _ in stage_data if sp]
        return step_paths


def _build_shaft_worker(stage_idx: int, stage: StageCadExport, next_stage: Optional[StageCadExport], spec: ShaftCadModelSpecification, step_path: Optional[str], visualize: bool = False, z_offset: float = 0.0, is_complex: bool = False):
    """Worker: builds a shaft stage, writes STEP to disk, optionally sends to viewer."""
    model = ShaftCadModel(stage, next_stage, spec, is_complex=is_complex)
    assembly = model.shaft_stage_assembly

    if step_path:
        assembly.export(step_path)

    if visualize:
        from jupyter_cadquery.viewer.client import show
        from turbodesigner.cad.cache import get_tessellation_cache, save_tessellation_cache
        positioned = cq.Assembly()
        positioned.add(assembly, loc=cq.Location(cq.Vector(0, 0, z_offset)))
        show(positioned, name=f"shaft-stage-{stage_idx+1}", accumulate=True, reset_camera=False, cache=get_tessellation_cache())
        save_tessellation_cache()
