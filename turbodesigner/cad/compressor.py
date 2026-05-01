from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import multiprocessing as mp
import cadquery as cq
from turbodesigner.cad.shaft import ShaftCadModel, ShaftCadModelSpecification
from turbodesigner.cad.casing import CasingCadModel, CasingCadModelSpecifciation
from turbodesigner.stage import StageCadExport
from turbodesigner.turbomachinery import TurbomachineryCadExport


@dataclass
class AxialStageCadModel:
    """Combined shaft + casing for a single axial compressor stage."""
    stage: StageCadExport
    first_stage: StageCadExport
    next_stage: Optional[StageCadExport] = None
    previous_stage: Optional[StageCadExport] = None
    shaft_spec: ShaftCadModelSpecification = field(default_factory=ShaftCadModelSpecification)
    casing_spec: CasingCadModelSpecifciation = field(default_factory=CasingCadModelSpecifciation)
    is_complex: bool = False

    @property
    def shaft_model(self) -> ShaftCadModel:
        return ShaftCadModel(self.stage, self.next_stage, self.shaft_spec, is_complex=self.is_complex)

    @property
    def casing_model(self) -> CasingCadModel:
        return CasingCadModel(self.stage, self.first_stage, self.previous_stage, self.casing_spec, is_complex=self.is_complex)

    @property
    def stage_axial_height(self) -> float:
        return self.stage.stage_gap + self.stage.stator.disk_height + self.stage.row_gap + self.stage.rotor.disk_height


@dataclass
class AxialCompressorCadModel:
    """Full axial compressor: shaft + casing for all stages."""
    turbomachinery: TurbomachineryCadExport
    shaft_spec: ShaftCadModelSpecification = field(default_factory=ShaftCadModelSpecification)
    casing_spec: CasingCadModelSpecifciation = field(default_factory=CasingCadModelSpecifciation)
    is_complex: bool = False

    @property
    def stages(self) -> list[AxialStageCadModel]:
        result = []
        for i, stage in enumerate(self.turbomachinery.stages):
            first_stage = self.turbomachinery.stages[0]
            next_stage = self.turbomachinery.stages[i + 1] if i + 1 < len(self.turbomachinery.stages) else None
            previous_stage = self.turbomachinery.stages[i - 1] if i > 0 else None
            result.append(AxialStageCadModel(
                stage=stage,
                first_stage=first_stage,
                next_stage=next_stage,
                previous_stage=previous_stage,
                shaft_spec=self.shaft_spec,
                casing_spec=self.casing_spec,
                is_complex=self.is_complex,
            ))
        return result

    @staticmethod
    def build_all(
        turbomachinery: TurbomachineryCadExport,
        shaft_spec: ShaftCadModelSpecification = ShaftCadModelSpecification(),
        casing_spec: CasingCadModelSpecifciation = CasingCadModelSpecifciation(),
        output_dir: Optional[Path] = None,
        visualize: bool = False,
        is_complex: bool = False,
    ) -> dict[str, list[str]]:
        """Build all shaft and casing stages in parallel and export STEP files.

        All stages (shaft + casing) are built concurrently. If visualize=True,
        each worker sends its result to the viewer with accumulate mode so all
        stages appear together properly offset.

        Args:
            turbomachinery: Full turbomachinery CAD export
            shaft_spec: Shaft CAD model specification
            casing_spec: Casing CAD model specification
            output_dir: Directory for STEP exports
            visualize: Send each stage to jupyter_cadquery viewer as it completes

        Returns:
            dict with 'shaft' and 'casing' keys containing lists of STEP file paths
        """
        first_stage = turbomachinery.stages[0]
        tasks = []  # (worker_fn, args)

        z_offset = 0.0
        for i in range(len(turbomachinery.stages)):
            stage = turbomachinery.stages[i]
            next_stage = turbomachinery.stages[i + 1] if i + 1 < len(turbomachinery.stages) else None
            previous_stage = turbomachinery.stages[i - 1] if i > 0 else None

            stage_height = stage.stage_gap + stage.stator.disk_height + stage.row_gap + stage.rotor.disk_height
            z_offset -= stage_height

            shaft_path = str(output_dir / f"shaft-stage-{stage.stage_number}.step") if output_dir else None
            casing_path = str(output_dir / f"casing-stage-{stage.stage_number}.step") if output_dir else None

            tasks.append((_build_stage_worker, (i, "shaft", stage, next_stage, previous_stage, first_stage, shaft_spec, casing_spec, shaft_path, visualize, z_offset, is_complex)))
            tasks.append((_build_stage_worker, (i, "casing", stage, next_stage, previous_stage, first_stage, shaft_spec, casing_spec, casing_path, visualize, z_offset, is_complex)))

        if visualize:
            from jupyter_cadquery.viewer.client import clear_viewer
            clear_viewer()

        ctx = mp.get_context("spawn")
        processes = []
        for worker_fn, args in tasks:
            p = ctx.Process(target=worker_fn, args=args)
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        if visualize:
            from jupyter_cadquery.viewer.client import flush_viewer
            flush_viewer()

        shaft_paths = [str(output_dir / f"shaft-stage-{s.stage_number}.step") for s in turbomachinery.stages] if output_dir else []
        casing_paths = [str(output_dir / f"casing-stage-{s.stage_number}.step") for s in turbomachinery.stages] if output_dir else []

        return {"shaft": shaft_paths, "casing": casing_paths}


def _build_stage_worker(
    stage_idx: int,
    component: str,
    stage: StageCadExport,
    next_stage: Optional[StageCadExport],
    previous_stage: Optional[StageCadExport],
    first_stage: StageCadExport,
    shaft_spec: ShaftCadModelSpecification,
    casing_spec: CasingCadModelSpecifciation,
    step_path: Optional[str],
    visualize: bool,
    z_offset: float,
    is_complex: bool = False,
):
    """Worker: builds a shaft or casing stage, exports STEP, optionally sends to viewer."""
    if component == "shaft":
        model = ShaftCadModel(stage, next_stage, shaft_spec, is_complex=is_complex)
        assembly = model.shaft_stage_assembly
        name = f"shaft-stage-{stage_idx+1}"
    else:
        model = CasingCadModel(stage, first_stage, previous_stage, casing_spec, is_complex=is_complex)
        assembly = model.casing_stage_assembly
        name = f"casing-stage-{stage_idx+1}"

    if step_path:
        assembly.export(step_path)

    if visualize:
        from jupyter_cadquery.viewer.client import show
        from turbodesigner.cad.cache import get_tessellation_cache, save_tessellation_cache
        positioned = cq.Assembly()
        positioned.add(assembly, loc=cq.Location(cq.Vector(0, 0, z_offset)))
        show(positioned, name=name, accumulate=True, reset_camera=False, cache=get_tessellation_cache())
        save_tessellation_cache()
