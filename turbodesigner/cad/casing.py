from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Optional
import multiprocessing as mp
from pydantic import BaseModel, Field
from turbodesigner.cad.blade import BladeCadModel, BladeCadModelSpecification
from turbodesigner.cad.common import CadColors, ExtendedWorkplane, FastenerPredicter, HeatSetDims, ScrewDims, colored_assembly
from turbodesigner.turbomachinery import TurbomachineryCadExport
from turbodesigner.stage import StageCadExport
import cadquery as cq
import numpy as np


class CasingCadModelSpecifciation(BaseModel):
    casing_thickness_to_inlet_radius: float = Field(default=0.25, description="Casing thickness to tip radius of first stage ratio")
    stage_connect_height_to_screw_head_diameter: float = Field(default=1.75, description="Casing stage connect to disk height ratio")
    stage_connect_padding_to_attachment_height: float = Field(default=1.25, description="Casing stage connect padding to attachment height ratio")
    stage_connect_heatset_diameter_to_disk_height: float = Field(default=0.25, description="Casing stage connect heatset diameter to disk height ratio")
    stage_connect_screw_quantity: int = Field(default=4, description="Number of screws per casing stage connection")
    casing_clamp_width_to_casing_thickness: float = Field(default=0.5, description="Casing clamp width to casing thickness ratio")


@dataclass
class CasingCadModel:
    stage: StageCadExport
    "turbomachinery stage"

    first_stage: StageCadExport
    "turbomachinery first stage"

    previous_stage: Optional[StageCadExport] = None
    "turbomachinery next stage"

    spec: CasingCadModelSpecifciation = field(default_factory=CasingCadModelSpecifciation)
    "casing cad model specification"

    is_complex: bool = False
    "whether to include fastener geometry"

    def __post_init__(self):
        # Use fast dimension lookups (no 3D geometry) for scalar calculations
        self._stage_connect_heatset_dims = FastenerPredicter.predict_heatset_dims(
            target_diameter=self.stage.rotor.disk_height*self.spec.stage_connect_heatset_diameter_to_disk_height,
        )

        self.casing_thickness = self.spec.casing_thickness_to_inlet_radius * self.first_stage.rotor.tip_radius
        self.casing_radius = self.first_stage.rotor.tip_radius+self.casing_thickness
        stage_connect_padding = self.spec.stage_connect_padding_to_attachment_height * self.stage.stator.attachment_height
        self.stage_connect_length = self.casing_thickness - stage_connect_padding - self.stage.stator.attachment_height

        self.blade_cad_model = BladeCadModel(
            self.stage.stator,
            spec=BladeCadModelSpecification(
                screw_length_padding=self.casing_thickness-self.stage.stator.attachment_height
            ),
            is_complex=self.is_complex,
        )

        screw_dims = FastenerPredicter.predict_screw_dims(
            target_diameter=self._stage_connect_heatset_dims.thread_diameter,
            target_length=self.stage_connect_length+self._stage_connect_heatset_dims.nut_thickness
        )

        self.stage_connect_height = screw_dims.head_diameter * self.spec.stage_connect_height_to_screw_head_diameter
        self.stage_connect_outer_radius = self.casing_radius
        self.stage_connect_inner_radius = self.stage_connect_outer_radius-self.stage_connect_length

        self.previous_stage_casing_cad_model: Optional[CasingCadModel] = None
        if self.previous_stage:
            self.previous_stage_casing_cad_model = CasingCadModel(self.previous_stage, self.first_stage, spec=self.spec)

        # Casing Clamp (use first_stage for consistent sizing across all stages)
        self.sector_angle = 360 / self.stage.stator.number_of_blades
        first_stage_sector_angle = 360 / self.first_stage.stator.number_of_blades
        self.casing_clamp_width = self.casing_thickness*self.spec.casing_clamp_width_to_casing_thickness
        self.casing_height = self.stage.stage_gap + self.stage.stage_height + self.stage.row_gap
        # Clamp block spans from bottom of stage connect ring to below previous stage pocket at top
        if self.previous_stage_casing_cad_model:
            self.casing_clamp_height = self.casing_height + self.stage_connect_height - self.previous_stage_casing_cad_model.stage_connect_height
        else:
            self.casing_clamp_height = self.casing_height + self.stage_connect_height
        self._casing_clamp_heatset_dims = FastenerPredicter.predict_heatset_dims(
            target_diameter=self.casing_clamp_width*0.4,
        )
        # Predict screw first, then derive clamp thickness from standard screw length
        self._casing_clamp_screw_dims = FastenerPredicter.predict_screw_dims(
            target_diameter=self._casing_clamp_heatset_dims.thread_diameter,
            target_length=self.casing_radius*np.sin(np.radians(first_stage_sector_angle) / 2)+self._casing_clamp_heatset_dims.nut_thickness/2
        )
        # Clamp thickness sized so standard screw passes through and seats into heatset
        self.casing_clamp_thickness = self._casing_clamp_screw_dims.length - self._casing_clamp_heatset_dims.nut_thickness/2

    @cached_property
    def stage_connect_heatset(self):
        return FastenerPredicter.predict_heatset(
            target_diameter=self.stage.rotor.disk_height*self.spec.stage_connect_heatset_diameter_to_disk_height,
        )

    @cached_property
    def stage_connect_screw(self):
        return FastenerPredicter.predict_screw(
            target_diameter=self._stage_connect_heatset_dims.thread_diameter,
            target_length=self.stage_connect_length+self._stage_connect_heatset_dims.nut_thickness
        )

    @cached_property
    def casing_clamp_heatset(self):
        return FastenerPredicter.predict_heatset(
            target_diameter=self.casing_clamp_width*0.4,
        )

    @cached_property
    def casing_clamp_screw(self):
        return FastenerPredicter.predict_screw(
            target_diameter=self._casing_clamp_heatset_dims.thread_diameter,
            target_length=self.casing_clamp_thickness+self._casing_clamp_heatset_dims.nut_thickness/2
        )

    @cached_property
    def casing_stage_assembly(self):
        base_assembly = cq.Assembly()
        blade_assembly = cq.Assembly()
        fastener_assembly = colored_assembly(CadColors.FASTENER)


        casing_cut_profile = (
            # Stator Disk
            ExtendedWorkplane("XY")
            .transformed(offset=(0, 0, -self.stage_connect_height))
            .circle(self.stage.stator.tip_radius*1.001)
            .extrude(self.stage.stator.disk_height+self.stage.stage_gap+self.stage_connect_height)

            # Transition Disk
            .faces(">Z")
            .workplane()
            .truncated_cone(
                start_radius=self.stage.stator.tip_radius,
                end_radius=self.stage.rotor.tip_radius,
                height=self.stage.row_gap
            )
            # Rotor Disk
            .faces(">Z")
            .workplane()
            .circle(self.stage.rotor.tip_radius)
            .extrude(self.stage.rotor.disk_height)
        )

        casing_profile = (
            ExtendedWorkplane("XY")
            .tag("split_center")
            .circle(self.first_stage.rotor.tip_radius + self.casing_thickness)
            .extrude(self.casing_height)
        )

        if self.is_complex:
            casing_profile = (
                casing_profile

                # Stage Shaft Connect
                .faces("<Z")
                .workplane()
                .circle(self.stage_connect_outer_radius)
                .circle(self.stage_connect_inner_radius)
                .extrude(self.stage_connect_height)

                # Add Casing Clamp (from bottom of stage connect to below previous stage pocket)
                .add(
                    cq.Workplane("XY")
                    .transformed(rotate=(0, 0, 90), offset=(0, 0, -self.stage_connect_height))
                    .box(self.casing_clamp_thickness*2, (self.casing_radius+self.casing_clamp_width)*2, self.casing_clamp_height, centered=(True, True, False))
                )
            )

        casing_profile = (
            casing_profile
            .cut(casing_cut_profile)
        )

        if self.is_complex:
            casing_profile = (
                casing_profile
                # Tag bottom workplane while geometry is still simple
                .faces("<Z")
                .workplane(offset=-self.stage_connect_height)
                .tag("stator_bottom")

                # Blade Lock Screws
                .workplane(offset=-self.stage.stator.attachment_height)
                .transformed(rotate=(0, 0, -self.sector_angle/2))
                .polarArray(self.stage_connect_outer_radius, 0, 360, self.stage.stator.number_of_blades)
                .mutatePoints(lambda loc: loc * cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 90))
                .clearanceHole(self.blade_cad_model.lock_screw, depth=self.blade_cad_model.lock_screw.length, fit="Loose", baseAssembly=fastener_assembly)

                # Stage Shaft Connect
                .faces("<Z")
                .workplane()
                .circle(self.stage_connect_inner_radius)
                .cutBlind(-self.stage_connect_height)

                # Stage Shaft Connect Screws
                .faces("<Z")
                .workplane(offset=-self.stage_connect_height/2)
                .transformed(rotate=(0, 0, 45))
                .polarArray(self.stage_connect_outer_radius, 0, 360, self.spec.stage_connect_screw_quantity)
                .mutatePoints(lambda loc: loc * cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 90))
                .clearanceHole(self.stage_connect_screw, fit="Loose", baseAssembly=fastener_assembly)
            )
            if self.previous_stage_casing_cad_model:
                casing_profile = (
                    casing_profile
                    # Previous Stage Shaft Connect
                    .faces(">Z")
                    .workplane()
                    .circle(self.previous_stage_casing_cad_model.stage_connect_outer_radius)
                    .circle(self.previous_stage_casing_cad_model.stage_connect_inner_radius)
                    .cutBlind(-self.previous_stage_casing_cad_model.stage_connect_height)

                    # Previous Stage Shaft Connect Heatsets
                    .faces(">Z")
                    .workplane(offset=-self.previous_stage_casing_cad_model.stage_connect_height/2)
                    .transformed(rotate=(0, 0, 45))
                    .polarArray(self.previous_stage_casing_cad_model.stage_connect_inner_radius, 0, 360, self.spec.stage_connect_screw_quantity)
                    .mutatePoints(lambda loc: loc * cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 90))
                    .insertHole(self.previous_stage_casing_cad_model.stage_connect_heatset, fit="Loose", baseAssembly=fastener_assembly, depth=self.previous_stage_casing_cad_model.stage_connect_heatset.nut_thickness)
                )
            # Cut Attachments LAST using spline (no face selection needed after)
            casing_profile = (
                casing_profile
                .workplaneFromTagged("stator_bottom")
                .transformed(rotate=(0, 0, -self.sector_angle/2))
                .polarArray(self.stage.stator.tip_radius, 0, 360, self.stage.stator.number_of_blades)
                .eachpoint(
                    lambda loc: (
                        cq.Workplane("XY")
                        .spline(self.stage.stator.attachment_with_tolerance[:-1].tolist())  # type: ignore
                        .close()
                        .rotate((0, 0, 0), (0, 0, 1), 90)

                    ).val().located(loc), True)  # type: ignore
                .cutBlind(-self.stage.stator.disk_height)
            )
        if self.is_complex:
            # Drill casing clamp holes BEFORE splitting (avoids face selection on split solids)
            # Drill casing clamp holes centered on casing body

            # Heatsets drill from split plane (Y=0) into -Y half (left)
            casing_profile = (
                casing_profile
                .workplaneFromTagged("split_center")
                .transformed(rotate=(-90, 0, 0), offset=(0, 0, -self.stage_connect_height + self.casing_clamp_height/2))
                .rect(self.casing_radius*2+self.casing_clamp_width, self.casing_height*0.5, forConstruction=True)
                .vertices()
                .insertHole(self.casing_clamp_heatset, fit="Loose", baseAssembly=fastener_assembly, depth=self.casing_clamp_heatset.nut_thickness)
            )
            # Clearance holes drill from split plane (Y=0) into +Y half (right)
            casing_profile = (
                casing_profile
                .workplaneFromTagged("split_center")
                .transformed(rotate=(-90, 0, 0), offset=(0, self.casing_clamp_thickness, -self.stage_connect_height + self.casing_clamp_height/2))
                .rect(self.casing_radius*2+self.casing_clamp_width, self.casing_height*0.5, forConstruction=True)
                .vertices()
                .clearanceHole(self.casing_clamp_screw, depth=self.casing_clamp_screw.length, fit="Loose", baseAssembly=fastener_assembly)
            )

            # Split into halves at Y=0 (XZ plane)
            left_casing_profile = (
                casing_profile
                .workplaneFromTagged("split_center")
                .transformed(rotate=(-90, 0, 0))
                .split(keepBottom=True)
            )
            right_casing_profile = (
                casing_profile
                .workplaneFromTagged("split_center")
                .transformed(rotate=(-90, 0, 0))
                .split(keepTop=True)
            )

            base_assembly.add(left_casing_profile, name=f"Left Casing", color=CadColors.CASING)
            base_assembly.add(right_casing_profile, name=f"Right Casing", color=CadColors.CASING)
        else:
            base_assembly.add(casing_profile, name=f"Casing", color=CadColors.CASING)

        blade_vertical_offset = self.stage.stator.disk_height/2
        blade_assembly_locs = (
            ExtendedWorkplane("XY")
            .polarArray(self.stage.stator.hub_radius, 0, 360, self.stage.stator.number_of_blades)
            .mutatePoints(lambda loc: loc * cq.Location(cq.Vector(0, 0, blade_vertical_offset), cq.Vector(0, 1, 0), 90))
            .vals()
        )

        for (i, blade_assembly_loc) in enumerate(blade_assembly_locs):
            assert isinstance(blade_assembly_loc, cq.Location)
            blade_assembly.add(self.blade_cad_model.blade_assembly, loc=blade_assembly_loc, name=f"Blade {i+1}")
        blade_assembly.rotate((0, 0, 1), -self.sector_angle/2)  # type: ignore

        base_assembly.add(blade_assembly, name="Blades")
        base_assembly.add(fastener_assembly, name="Fasteners")

        return base_assembly

    @staticmethod
    def build_assembly(stage: StageCadExport, first_stage: StageCadExport, previous_stage: Optional[StageCadExport] = None, spec: CasingCadModelSpecifciation = CasingCadModelSpecifciation(), output_dir: Optional[Path] = None, visualize: bool = False, accumulate: bool = False, is_complex: bool = False):
        """Build a single casing stage assembly.

        Args:
            stage: Stage CAD export data
            first_stage: First stage CAD export data (for casing thickness)
            previous_stage: Previous stage for connect geometry
            spec: Casing CAD model specification
            output_dir: Directory for STEP export (exports if provided)
            visualize: Send result to jupyter_cadquery viewer

        Returns:
            cq.Assembly for this stage
        """
        model = CasingCadModel(stage, first_stage, previous_stage, spec, is_complex=is_complex)
        assembly = model.casing_stage_assembly

        if output_dir:
            step_path = str(output_dir / f"casing-stage-{stage.stage_number}.step")
            assembly.export(step_path)

        if visualize:
            from jupyter_cadquery.viewer.client import show
            from turbodesigner.cad.cache import get_tessellation_cache, save_tessellation_cache
            show(assembly, name=f"casing-stage-{stage.stage_number}", accumulate=accumulate, reset_camera=not accumulate, cache=get_tessellation_cache())
            save_tessellation_cache()

        return assembly

    @staticmethod
    def build_all(turbomachinery: TurbomachineryCadExport, spec: CasingCadModelSpecifciation = CasingCadModelSpecifciation(), output_dir: Optional[Path] = None, visualize: bool = False, is_complex: bool = False):
        """Build all casing stages in parallel subprocesses and export STEP files.

        Each stage is built in a subprocess with export=True. The combined
        assembly is reassembled from BREP bytes for optional visualization.

        Args:
            turbomachinery: Full turbomachinery CAD export
            spec: Casing CAD model specification
            output_dir: Directory for STEP exports (required)
            visualize: Send combined assembly to jupyter_cadquery viewer

        Returns:
            list[str]: Paths to exported STEP files
        """
        first_stage = turbomachinery.stages[0]
        stage_data = []
        z_offset = 0.0
        for i in range(len(turbomachinery.stages)):
            stage = turbomachinery.stages[i]
            previous_stage = turbomachinery.stages[i - 1] if i > 0 else None
            stage_height = stage.stage_gap + stage.stator.disk_height + stage.row_gap + stage.rotor.disk_height
            z_offset -= stage_height
            step_path = str(output_dir / f"casing-stage-{stage.stage_number}.step") if output_dir else None
            stage_data.append((i, stage, first_stage, previous_stage, step_path, z_offset))

        if visualize:
            from jupyter_cadquery.viewer.client import clear_viewer
            clear_viewer()

        ctx = mp.get_context("spawn")
        processes = []
        for i, stage, first_stage_ref, previous_stage, step_path, z_off in stage_data:
            p = ctx.Process(target=_build_casing_worker, args=(i, stage, first_stage_ref, previous_stage, spec, step_path, visualize, z_off, is_complex))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        if visualize:
            from jupyter_cadquery.viewer.client import flush_viewer
            flush_viewer()

        step_paths = [sp for _, _, _, _, sp, _ in stage_data if sp]
        return step_paths


def _build_casing_worker(stage_idx: int, stage: StageCadExport, first_stage: StageCadExport, previous_stage: Optional[StageCadExport], spec: CasingCadModelSpecifciation, step_path: Optional[str], visualize: bool = False, z_offset: float = 0.0, is_complex: bool = False):
    """Worker: builds a casing stage, writes STEP to disk, optionally sends to viewer."""
    model = CasingCadModel(stage, first_stage, previous_stage, spec, is_complex=is_complex)
    assembly = model.casing_stage_assembly

    if step_path:
        assembly.export(step_path)

    if visualize:
        from jupyter_cadquery.viewer.client import show
        from turbodesigner.cad.cache import get_tessellation_cache, save_tessellation_cache
        positioned = cq.Assembly()
        positioned.add(assembly, loc=cq.Location(cq.Vector(0, 0, z_offset)))
        show(positioned, name=f"casing-stage-{stage_idx+1}", accumulate=True, reset_camera=False, cache=get_tessellation_cache())
        save_tessellation_cache()
