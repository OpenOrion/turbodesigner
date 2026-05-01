"""Exporter: generates pandas DataFrames from pydantic model computed outputs."""
import numpy as np
import pandas as pd
from functools import cached_property
from pydantic import BaseModel
from turbodesigner.turbomachinery import Turbomachinery


def _is_scalar(val) -> bool:
    if isinstance(val, (int, float, bool, str)):
        return True
    if isinstance(val, np.floating):
        return True
    if isinstance(val, list) and all(isinstance(v, (int, float)) for v in val):
        return True
    if isinstance(val, np.ndarray):
        return True
    return False


def _scalar_val(val):
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, np.floating):
        return float(val)
    if isinstance(val, np.integer):
        return int(val)
    return val


def _get_cached_properties(obj: BaseModel) -> dict[str, any]:
    """Get cached_property scalar values with labels (not input fields)."""
    cls = type(obj)
    result = {}

    for name in dir(cls):
        if name.startswith("_"):
            continue
        attr = getattr(cls, name, None)
        if not isinstance(attr, cached_property):
            continue
        try:
            val = getattr(obj, name)
        except (AssertionError, AttributeError, TypeError, ValueError):
            continue
        if not _is_scalar(val):
            continue
        doc = attr.func.__doc__
        label = doc.strip() if doc else name
        result[label] = _scalar_val(val)

    return result


def _get_sub_model_cached_properties(obj: BaseModel) -> dict[str, BaseModel]:
    """Get cached_property values that are themselves BaseModel instances."""
    cls = type(obj)
    result = {}

    for name in dir(cls):
        if name.startswith("_"):
            continue
        attr = getattr(cls, name, None)
        if not isinstance(attr, cached_property):
            continue
        try:
            val = getattr(obj, name)
        except (AssertionError, AttributeError, TypeError, ValueError):
            continue
        if isinstance(val, BaseModel):
            result[name] = val

    return result


def dataclass_to_df(obj: BaseModel) -> pd.DataFrame:
    """Convert a pydantic model to a single-column DataFrame of cached properties."""
    rows = _get_cached_properties(obj)
    return pd.DataFrame.from_dict(rows, orient="index", columns=["Value"])


def dataclass_list_to_df(objects: list[BaseModel]) -> pd.DataFrame:
    """Convert a list of pydantic models to a DataFrame. Properties as rows, stages as columns."""
    data = {}
    for i, obj in enumerate(objects):
        row = _get_cached_properties(obj)
        data[f"Stage {i + 1}"] = row
    return pd.DataFrame(data)


def flow_station_to_row(fs: BaseModel, prefix: str = "") -> dict:
    """Convert a FlowStation to a flat dict with labeled keys (all scalar props)."""
    props = _get_cached_properties(fs)
    if prefix:
        return {f"{prefix}{k}": v for k, v in props.items()}
    return props


def stages_flow_stations_df(turbomachinery: Turbomachinery) -> pd.DataFrame:
    """Per-stage inlet + mid flow station properties. Properties as rows, stages as columns."""
    data = {}
    for stage in turbomachinery.stages:
        col = {}
        col.update(flow_station_to_row(stage.inlet_flow_station, "inlet "))
        col.update(flow_station_to_row(stage.mid_flow_station, "mid "))
        data[f"Stage {stage.stage_number}"] = col
    return pd.DataFrame(data)


def stages_blade_rows_df(turbomachinery: Turbomachinery) -> pd.DataFrame:
    """Per-stage rotor + stator scalar blade row properties. Properties as rows, stages as columns."""
    data = {}
    for stage in turbomachinery.stages:
        rotor_props = _get_cached_properties(stage.rotor)
        stator_props = _get_cached_properties(stage.stator)
        col = {}
        all_keys = list(dict.fromkeys(list(rotor_props.keys()) + list(stator_props.keys())))
        for k in all_keys:
            r_val = rotor_props.get(k)
            s_val = stator_props.get(k)
            if isinstance(r_val, list) or isinstance(s_val, list):
                continue
            col[f"Rotor {k}"] = r_val if r_val is not None else "-"
            col[f"Stator {k}"] = s_val if s_val is not None else "-"
        data[f"Stage {stage.stage_number}"] = col
    return pd.DataFrame(data)


def stages_blade_rows_streams_df(turbomachinery: Turbomachinery) -> pd.DataFrame:
    """Per-stage rotor + stator per-stream blade row properties. Arrays expanded to hub/stream/tip rows."""
    data = {}
    for stage in turbomachinery.stages:
        rotor_props = _get_cached_properties(stage.rotor)
        stator_props = _get_cached_properties(stage.stator)
        col = {}
        all_keys = list(dict.fromkeys(list(rotor_props.keys()) + list(stator_props.keys())))
        for k in all_keys:
            r_val = rotor_props.get(k)
            s_val = stator_props.get(k)
            r_is_arr = isinstance(r_val, list)
            s_is_arr = isinstance(s_val, list)
            if not r_is_arr and not s_is_arr:
                continue
            r_arr = r_val if r_is_arr else []
            s_arr = s_val if s_is_arr else []
            n = max(len(r_arr), len(s_arr))
            if n == 3:
                suffixes = ["hub", "mean", "tip"]
            elif n > 3:
                suffixes = ["hub"] + [f"stream {i+1}" for i in range(1, n - 1)] + ["tip"]
            else:
                suffixes = [str(i) for i in range(n)]
            for j, sfx in enumerate(suffixes):
                col[f"Rotor {k} [{sfx}]"] = r_arr[j] if j < len(r_arr) else None
                col[f"Stator {k} [{sfx}]"] = s_arr[j] if j < len(s_arr) else None
        data[f"Stage {stage.stage_number}"] = col
    return pd.DataFrame(data)


def stages_blade_rows_sub_models_dfs(turbomachinery: Turbomachinery) -> dict[str, pd.DataFrame]:
    """Per-stage rotor + stator sub-model properties. Returns {section_name: DataFrame}."""
    # Discover sub-model names from the first stage's rotor
    first_rotor = turbomachinery.stages[0].rotor
    sub_model_names = list(_get_sub_model_cached_properties(first_rotor).keys())

    results = {}
    for sm_name in sub_model_names:
        data = {}
        for stage in turbomachinery.stages:
            col = {}
            try:
                rotor_sm = getattr(stage.rotor, sm_name)
            except (AssertionError, AttributeError, TypeError, ValueError):
                rotor_sm = None
            try:
                stator_sm = getattr(stage.stator, sm_name)
            except (AssertionError, AttributeError, TypeError, ValueError):
                stator_sm = None

            rotor_props = _get_cached_properties(rotor_sm) if rotor_sm else {}
            stator_props = _get_cached_properties(stator_sm) if stator_sm else {}
            all_keys = list(dict.fromkeys(list(rotor_props.keys()) + list(stator_props.keys())))
            for k in all_keys:
                r_val = rotor_props.get(k)
                s_val = stator_props.get(k)
                r_is_arr = isinstance(r_val, list)
                s_is_arr = isinstance(s_val, list)
                if r_is_arr or s_is_arr:
                    r_arr = r_val if r_is_arr else []
                    s_arr = s_val if s_is_arr else []
                    n = max(len(r_arr), len(s_arr))
                    if n == 3:
                        suffixes = ["hub", "mean", "tip"]
                    elif n > 3:
                        suffixes = ["hub"] + [f"stream {i+1}" for i in range(1, n - 1)] + ["tip"]
                    else:
                        suffixes = [str(i) for i in range(n)]
                    for j, sfx in enumerate(suffixes):
                        col[f"Rotor {k} [{sfx}]"] = r_arr[j] if j < len(r_arr) else None
                        col[f"Stator {k} [{sfx}]"] = s_arr[j] if j < len(s_arr) else None
                else:
                    col[f"Rotor {k}"] = r_val
                    col[f"Stator {k}"] = s_val
            data[f"Stage {stage.stage_number}"] = col
        results[sm_name] = pd.DataFrame(data)
    return results


def machine_properties_df(turbomachinery: Turbomachinery) -> pd.DataFrame:
    """Turbomachinery-level cached properties as a single-column DataFrame."""
    rows = _get_cached_properties(turbomachinery)
    return pd.DataFrame.from_dict(rows, orient="index", columns=["Value"])
