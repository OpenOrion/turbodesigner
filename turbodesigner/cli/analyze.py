import click

import pandas as pd

from turbodesigner.cli.state import load_design
from turbodesigner.cli.utils import design_option


@click.group()
def analyze() -> None:
    """Run mean-line analysis on the active design."""
    pass


def _format_options(fn):
    fn = click.option("--csv", "use_csv", is_flag=True, help="Output as CSV")(fn)
    return fn


def _output_df(ctx: click.Context, df: pd.DataFrame, use_csv: bool) -> None:
    """Output a DataFrame in the appropriate format."""
    fmt = ctx.obj["fmt"]
    if fmt.use_json:
        fmt.output(df.to_dict())
    elif use_csv:
        click.echo(df.to_csv())
    else:
        click.echo(df.to_string())


@analyze.command("machine")
@design_option
@_format_options
@click.pass_context
def analyze_machine(ctx: click.Context, design_name: str | None, use_csv: bool) -> None:
    """Show all turbomachinery-level properties (auto-generated from model fields)."""
    fmt = ctx.obj["fmt"]
    try:
        _, tm = load_design(design_name)
    except ValueError as e:
        fmt.error(str(e))
        return

    from turbodesigner.exporter import machine_properties_df
    df = machine_properties_df(tm)
    _output_df(ctx, df, use_csv)


@analyze.command("stages")
@design_option
@_format_options
@click.pass_context
def analyze_stages(ctx: click.Context, design_name: str | None, use_csv: bool) -> None:
    """Show all per-stage scalar properties (auto-generated from Stage dataclass)."""
    fmt = ctx.obj["fmt"]
    try:
        _, tm = load_design(design_name)
    except ValueError as e:
        fmt.error(str(e))
        return

    from turbodesigner.exporter import dataclass_list_to_df
    df = dataclass_list_to_df(tm.stages)
    _output_df(ctx, df, use_csv)


@analyze.command("flow-stations")
@design_option
@_format_options
@click.pass_context
def analyze_flow_stations(ctx: click.Context, design_name: str | None, use_csv: bool) -> None:
    """Show per-stage inlet + mid flow station properties (auto-generated from FlowStation)."""
    fmt = ctx.obj["fmt"]
    try:
        _, tm = load_design(design_name)
    except ValueError as e:
        fmt.error(str(e))
        return

    from turbodesigner.exporter import stages_flow_stations_df
    df = stages_flow_stations_df(tm)
    _output_df(ctx, df, use_csv)


@analyze.command("blade-rows")
@design_option
@_format_options
@click.pass_context
def analyze_blade_rows(ctx: click.Context, design_name: str | None, use_csv: bool) -> None:
    """Show per-stage rotor + stator blade row properties (auto-generated from BladeRow)."""
    fmt = ctx.obj["fmt"]
    try:
        _, tm = load_design(design_name)
    except ValueError as e:
        fmt.error(str(e))
        return

    from turbodesigner.exporter import stages_blade_rows_df, stages_blade_rows_streams_df, stages_blade_rows_sub_models_dfs
    df = stages_blade_rows_df(tm)
    df_streams = stages_blade_rows_streams_df(tm)
    sub_models = stages_blade_rows_sub_models_dfs(tm)

    if fmt.use_json:
        combined: dict[str, object] = {
            "blade_rows": df.to_dict(),
            "per_stream": df_streams.to_dict(),
        }
        for section_name, df_sm in sub_models.items():
            combined[section_name] = df_sm.to_dict()
        fmt.output(combined)
    else:
        _output_df(ctx, df, use_csv)
        click.echo("")
        click.echo("--- Per-Stream Properties ---")
        click.echo("")
        _output_df(ctx, df_streams, use_csv)
        for section_name, df_sm in sub_models.items():
            click.echo("")
            click.echo(f"--- {section_name.replace('_', ' ').title()} ---")
            click.echo("")
            _output_df(ctx, df_sm, use_csv)



