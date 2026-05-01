"""Bill of Materials generation for turbomachinery CAD assemblies."""
import csv
from pathlib import Path
from typing import Optional

from turbodesigner.cad.blade import BladeCadModel, BladeCadModelSpecification
from turbodesigner.cad.casing import CasingCadModel, CasingCadModelSpecifciation
from turbodesigner.cad.shaft import ShaftCadModel, ShaftCadModelSpecification
from turbodesigner.turbomachinery import TurbomachineryCadExport


def generate_bom(
    turbomachinery: TurbomachineryCadExport,
    output_dir: Path,
    shaft_spec: ShaftCadModelSpecification = ShaftCadModelSpecification(),
    casing_spec: CasingCadModelSpecifciation = CasingCadModelSpecifciation(),
) -> str:
    """Generate a Bill of Materials CSV for the full assembly.

    Includes fasteners (heatsets, screws) and structural parts (blades, disks, casings).

    Returns:
        Path to the generated BOM.csv file.
    """
    bom: dict[str, dict] = {}  # key: part description, value: {quantity, category, component}

    first_stage = turbomachinery.stages[0]

    for i, stage in enumerate(turbomachinery.stages):
        next_stage = turbomachinery.stages[i + 1] if i + 1 < len(turbomachinery.stages) else None
        previous_stage = turbomachinery.stages[i - 1] if i > 0 else None
        stage_num = stage.stage_number

        # --- Shaft model ---
        shaft = ShaftCadModel(stage, next_stage, shaft_spec, is_complex=False)

        # Shaft stage connect fasteners
        _add_fastener(bom, shaft.stage_connect_heatset, shaft_spec.stage_connect_screw_quantity, f"Shaft Stage {stage_num}")
        _add_fastener(bom, shaft.stage_connect_screw, shaft_spec.stage_connect_screw_quantity, f"Shaft Stage {stage_num}")

        # Rotor blade fasteners (1 heatset + 1 screw per blade)
        rotor_blade = shaft.blade_cad_model
        _add_fastener(bom, rotor_blade.heatset, stage.rotor.number_of_blades, f"Rotor Blade Stage {stage_num}")
        _add_fastener(bom, rotor_blade.lock_screw, stage.rotor.number_of_blades, f"Rotor Blade Stage {stage_num}")

        # Next stage connect screws (shaft side)
        if next_stage and shaft.next_stage_shaft_cad_model:
            next_screw = shaft.next_stage_stage_connect_screw
            _add_fastener(bom, next_screw, shaft_spec.stage_connect_screw_quantity, f"Shaft Stage {stage_num}")

        # --- Casing model ---
        casing = CasingCadModel(stage, first_stage, previous_stage, casing_spec, is_complex=False)

        # Casing stage connect fasteners
        _add_fastener(bom, casing.stage_connect_heatset, casing_spec.stage_connect_screw_quantity, f"Casing Stage {stage_num}")
        _add_fastener(bom, casing.stage_connect_screw, casing_spec.stage_connect_screw_quantity, f"Casing Stage {stage_num}")

        # Casing clamp fasteners (1 per stator blade)
        _add_fastener(bom, casing.casing_clamp_heatset, stage.stator.number_of_blades, f"Casing Clamp Stage {stage_num}")
        _add_fastener(bom, casing.casing_clamp_screw, stage.stator.number_of_blades, f"Casing Clamp Stage {stage_num}")

        # Stator blade fasteners (1 heatset + 1 screw per blade)
        stator_blade = casing.blade_cad_model
        _add_fastener(bom, stator_blade.heatset, stage.stator.number_of_blades, f"Stator Blade Stage {stage_num}")
        _add_fastener(bom, stator_blade.lock_screw, stage.stator.number_of_blades, f"Stator Blade Stage {stage_num}")

        # --- Structural parts ---
        _add_part(bom, f"Rotor Blade (Stage {stage_num})", stage.rotor.number_of_blades, "Blade")
        _add_part(bom, f"Stator Blade (Stage {stage_num})", stage.stator.number_of_blades, "Blade")
        _add_part(bom, f"Shaft Disk (Stage {stage_num})", 1, "Shaft")
        _add_part(bom, f"Casing Section (Stage {stage_num})", 1, "Casing")
        _add_part(bom, f"Casing Clamp (Stage {stage_num})", stage.stator.number_of_blades, "Casing")

    # Write CSV
    output_dir.mkdir(parents=True, exist_ok=True)
    bom_path = output_dir / "BOM.csv"

    rows = []
    for part_desc, info in sorted(bom.items(), key=lambda x: (x[1]["category"], x[0])):
        rows.append({
            "Part": part_desc,
            "Quantity": info["quantity"],
            "Category": info["category"],
            "Component": info["component"],
        })

    with open(bom_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Part", "Quantity", "Category", "Component"])
        writer.writeheader()
        writer.writerows(rows)

    return str(bom_path)


def _add_fastener(bom: dict, fastener, quantity: int, component: str):
    """Add a fastener to the BOM dict, aggregating quantities."""
    info_lines = fastener.info.split("\n")
    part_desc = info_lines[0] if info_lines else str(fastener)

    if part_desc in bom:
        bom[part_desc]["quantity"] += quantity
        # Track all components that use this fastener
        if component not in bom[part_desc]["component"]:
            bom[part_desc]["component"] += f"; {component}"
    else:
        bom[part_desc] = {
            "quantity": quantity,
            "category": "Fastener",
            "component": component,
        }


def _add_part(bom: dict, part_desc: str, quantity: int, category: str):
    """Add a structural part to the BOM dict."""
    if part_desc in bom:
        bom[part_desc]["quantity"] += quantity
    else:
        bom[part_desc] = {
            "quantity": quantity,
            "category": category,
            "component": part_desc,
        }
