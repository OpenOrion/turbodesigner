"""Workspace state management for turbodesigner CLI.

State is stored in .turbodesigner/ in the current working directory:
  .turbodesigner/config.json       - active design name
  .turbodesigner/designs/<name>/   - per-design folder
    design.json                    - design parameters
    output/                        - CAD output files (STEP, etc.)
  .turbodesigner/cache/            - cached tessellation data
"""
import json
import os
import shutil
from pathlib import Path
from typing import Any, Optional, Union

WORKSPACE_DIR_NAME = ".turbodesigner"

from pydantic import BaseModel, Field
from turbodesigner.turbomachinery import Turbomachinery
from turbodesigner.cad.shaft import ShaftCadModelSpecification
from turbodesigner.cad.casing import CasingCadModelSpecifciation
from turbodesigner.cad.blade import BladeCadModelSpecification


class CadSpec(BaseModel):
    """CAD specifications for all components."""
    shaft: ShaftCadModelSpecification = Field(default_factory=ShaftCadModelSpecification, description="Shaft geometry parameters")
    casing: CasingCadModelSpecifciation = Field(default_factory=CasingCadModelSpecifciation, description="Casing geometry parameters")
    blade: BladeCadModelSpecification = Field(default_factory=BladeCadModelSpecification, description="Blade geometry parameters")


class TurboDesign(BaseModel):
    """Structured export format for a turbodesigner design file."""
    machine_type: str = Field(default="axial", description="Machine type (axial, centrifugal, mixed_flow)")
    configuration: str = Field(default="compressor", description="Machine configuration (compressor, turbine, fan)")
    definition: Turbomachinery = Field(description="Turbomachinery design definition")
    cad: CadSpec = Field(default_factory=CadSpec, description="CAD specifications per component")

    @staticmethod
    def from_file(file_name: str) -> "TurboDesign":
        with open(file_name, "r") as fp:
            obj = json.load(fp)
        if "definition" not in obj:
            obj = {"definition": obj}
        return TurboDesign.model_validate(obj)


def get_workspace_dir() -> Path:
    """Find the .turbodesigner/ directory by walking up from CWD (like git finds .git/).

    Search order:
      1. TURBODESIGNER_WORKSPACE env var (explicit override)
      2. Walk up from CWD looking for existing .turbodesigner/
      3. Fall back to CWD/.turbodesigner/ (for init/create)
    """
    env_ws = os.environ.get("TURBODESIGNER_WORKSPACE")
    if env_ws:
        return Path(env_ws) / WORKSPACE_DIR_NAME

    current = Path.cwd()
    while True:
        candidate = current / WORKSPACE_DIR_NAME
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent

    return Path.cwd() / WORKSPACE_DIR_NAME


def ensure_workspace() -> Path:
    """Ensure .turbodesigner/ directory structure exists."""
    ws = get_workspace_dir()
    (ws / "designs").mkdir(parents=True, exist_ok=True)
    (ws / "cache").mkdir(parents=True, exist_ok=True)
    if not (ws / "config.json").exists():
        (ws / "config.json").write_text(json.dumps({"active_design": None}, indent=2))
    return ws


def get_config() -> dict[str, Any]:
    """Read workspace config."""
    ws = get_workspace_dir()
    config_path = ws / "config.json"
    if not config_path.exists():
        return {"active_design": None}
    return json.loads(config_path.read_text())


def set_config(config: dict[str, Any]) -> None:
    """Write workspace config."""
    ws = ensure_workspace()
    (ws / "config.json").write_text(json.dumps(config, indent=2))


def get_active_design_name() -> Optional[str]:
    """Get the name of the active design."""
    return get_config().get("active_design")


def set_active_design(name: str) -> None:
    """Set the active design name."""
    config = get_config()
    config["active_design"] = name
    set_config(config)


def list_designs() -> list[str]:
    """List all design names in the workspace."""
    ws = get_workspace_dir()
    designs_dir = ws / "designs"
    if not designs_dir.exists():
        return []
    return sorted(p.name for p in designs_dir.iterdir() if p.is_dir() and (p / "design.json").exists())


def get_design_path(name: str) -> Optional[Path]:
    """Get the path to a design JSON file by name."""
    ws = get_workspace_dir()
    path = ws / "designs" / name / "design.json"
    if path.exists():
        return path
    return None


def clear_active_design() -> None:
    """Clear the active design (set to null)."""
    config = get_config()
    config["active_design"] = None
    set_config(config)


def resolve_design(name: Optional[str]) -> tuple[str, Path]:
    """Resolve a design name to its path. Uses active design if name is None.

    Returns (name, path) tuple.
    Raises ValueError if design cannot be resolved.
    """
    if name is None:
        name = get_active_design_name()
        if name is None:
            raise ValueError(
                "No active design set. Use 'turbodesigner axial compressor design use <name>' or pass --design <name>"
            )
    path = get_design_path(name)
    if path is None:
        clear_active_design()
        raise ValueError(f"Design '{name}' does not exist. Active design has been cleared.")
    return name, path


def load_design_export(name: str) -> TurboDesign:
    """Load a TurboDesign from the workspace."""
    data = _load_design_json(name)
    if "definition" not in data:
        data = {"definition": data}
    return TurboDesign.model_validate(data)


def save_design_export(name: str, export: TurboDesign) -> str:
    """Save a TurboDesign to the workspace. Returns the file path."""
    _save_design_json(name, export.model_dump())
    ws = ensure_workspace()
    return str(ws / "designs" / name / "design.json")


def load_design(name: Optional[str] = None) -> tuple[str, Turbomachinery]:
    """Load a Turbomachinery object by design name.

    Returns (name, turbomachinery) tuple.
    """
    name, path = resolve_design(name)
    export = load_design_export(name)
    return name, export.definition


def save_design(name: str, source_path: str, machine_type: str = "axial", configuration: str = "compressor") -> str:
    """Import a design JSON file into the workspace as a TurboDesign. Returns the file path."""
    ws = ensure_workspace()
    with open(source_path) as f:
        source_data = json.load(f)
    if "definition" not in source_data:
        source_data = {"definition": source_data, "machine_type": machine_type, "configuration": configuration}
    export = TurboDesign.model_validate(source_data)
    return save_design_export(name, export)


def save_design_from_json(name: str, json_str: str, machine_type: str = "axial", configuration: str = "compressor") -> str:
    """Import a design from an inline JSON string into the workspace as a TurboDesign. Returns the file path."""
    ensure_workspace()
    source_data = json.loads(json_str)
    if "definition" not in source_data:
        source_data = {"definition": source_data, "machine_type": machine_type, "configuration": configuration}
    export = TurboDesign.model_validate(source_data)
    return save_design_export(name, export)


def delete_design(name: str) -> bool:
    """Delete a design from the workspace. Returns True if deleted."""
    ws = get_workspace_dir()
    design_dir = ws / "designs" / name
    if design_dir.exists():
        shutil.rmtree(design_dir)
        # Clear active if this was active
        if get_active_design_name() == name:
            config = get_config()
            config["active_design"] = None
            set_config(config)
        return True
    return False


def get_output_dir(design_name: str) -> Path:
    """Get the output directory for a design."""
    ws = ensure_workspace()
    output = ws / "designs" / design_name / "output"
    output.mkdir(parents=True, exist_ok=True)
    return output


def _load_design_json(name: str) -> dict[str, Any]:
    """Load raw design JSON as dict."""
    path = get_design_path(name)
    if path is None:
        raise ValueError(f"Design '{name}' not found.")
    return json.loads(path.read_text())


def _save_design_json(name: str, data: dict[str, Any]) -> None:
    """Save design JSON dict."""
    ws = ensure_workspace()
    design_dir = ws / "designs" / name
    design_dir.mkdir(parents=True, exist_ok=True)
    path = design_dir / "design.json"
    path.write_text(json.dumps(data, indent=4))


def load_shaft_spec(design_name: str) -> ShaftCadModelSpecification:
    """Load ShaftCadModelSpecification from design."""
    export = load_design_export(design_name)
    return export.cad.shaft.model_copy()


def load_casing_spec(design_name: str) -> CasingCadModelSpecifciation:
    """Load CasingCadModelSpecifciation from design."""
    export = load_design_export(design_name)
    return export.cad.casing.model_copy()


def load_blade_spec(design_name: str) -> BladeCadModelSpecification:
    """Load BladeCadModelSpecification from design."""
    export = load_design_export(design_name)
    return export.cad.blade.model_copy()


def save_cad_spec(design_name: str, component: str, spec: Union[ShaftCadModelSpecification, CasingCadModelSpecifciation, BladeCadModelSpecification]) -> None:
    """Save a CAD spec model into the design."""
    export = load_design_export(design_name)
    setattr(export.cad, component, spec)
    save_design_export(design_name, export)


def get_cad_spec_summary(design_name: str) -> dict[str, Any]:
    """Get a summary of stored CAD specifications for a design."""
    export = load_design_export(design_name)
    return export.cad.model_dump()

