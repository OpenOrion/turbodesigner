import click

from turbodesigner.cli.state import (
    ensure_workspace,
    list_designs,
    get_design_path,
    load_design,
    save_design,
    save_design_from_json,
    get_active_design_name,
    set_active_design,
    resolve_design,
    get_cad_spec_summary,
    save_cad_spec,
    load_shaft_spec,
    load_casing_spec,
    load_blade_spec,
)


@click.group()
def design() -> None:
    """Manage turbomachinery designs in the workspace."""
    pass


@design.command("schema")
@click.pass_context
def design_schema(ctx: click.Context) -> None:
    """Show the design JSON schema.

    \b
    AI AGENTS: Read this schema to understand the design format, then
    pass inline JSON to 'design create --json'.
    """
    import json as json_mod
    fmt = ctx.obj["fmt"]

    from turbodesigner.cli.state import TurboDesign

    schema = TurboDesign.model_json_schema(mode='serialization')
    if fmt.use_json:
        fmt.output(schema)
    else:
        click.echo(json_mod.dumps(schema, indent=2))


@design.command("create")
@click.argument("name")
@click.option("--from", "from_path", type=click.Path(exists=True), default=None, help="Path to design JSON file")
@click.option("--json", "inline_json", type=str, default=None, help="Inline JSON string (use '-' to read from stdin)")
@click.pass_context
def design_create(ctx: click.Context, name: str, from_path: str | None, inline_json: str | None) -> None:
    """Import a design into the workspace.

    \b
    AI AGENTS: Use --json with inline JSON directly. Do NOT write temp files.
      turbodesigner axial compressor design create NAME --json '{...}'
      echo '{...}' | turbodesigner axial compressor design create NAME --json -
    """
    fmt = ctx.obj["fmt"]
    ensure_workspace()

    if not from_path and not inline_json:
        fmt.error("Provide either --from <file> or --json '<json string>'")

    if inline_json:
        import sys
        json_str = sys.stdin.read() if inline_json == "-" else inline_json
        design_path = save_design_from_json(name, json_str)
        result = {"name": name, "source": "stdin" if inline_json == "-" else "inline JSON", "status": "created", "file": design_path}
    else:
        design_path = save_design(name, from_path)
        result = {"name": name, "source": from_path, "status": "created", "file": design_path}

    set_active_design(name)
    fmt.output(result, lambda d: f"Created design '{d['name']}' from {d['source']}\nDesign file: {d['file']}\nYou can edit this file directly to modify the design.")


@design.command("list")
@click.pass_context
def design_list(ctx: click.Context) -> None:
    """List all designs in the workspace."""
    fmt = ctx.obj["fmt"]
    designs = list_designs()
    active = get_active_design_name()

    if fmt.use_json:
        fmt.output({"designs": designs, "active": active})
    else:
        if not designs:
            click.echo("No designs found. Use 'turbodesigner axial compressor design create <name> --from <path>' to add one.")
            return
        for d in designs:
            marker = " (active)" if d == active else ""
            click.echo(f"  {d}{marker}")


@design.command("use")
@click.argument("name")
@click.pass_context
def design_use(ctx: click.Context, name: str) -> None:
    """Set the active design for subsequent commands."""
    fmt = ctx.obj["fmt"]

    if get_design_path(name) is None:
        fmt.error(f"Design '{name}' not found. Use 'turbodesigner axial compressor design list' to see available designs.")

    set_active_design(name)
    result = {"name": name, "status": "active"}
    fmt.output(result, lambda d: f"Active design set to '{d['name']}'")


@design.command("show")
@click.argument("name", required=False)
@click.pass_context
def design_show(ctx: click.Context, name: str | None) -> None:
    """Show summary of a design (active design if no name given)."""
    fmt = ctx.obj["fmt"]
    try:
        design_name, tm = load_design(name)
    except ValueError as e:
        fmt.error(str(e))
        return

    summary = {"name": design_name, **tm.model_dump(), "cad": get_cad_spec_summary(design_name)}
    fmt.output(summary, lambda d: "\n".join(
        [f"Design: {d['name']}"] + [f"  {k}: {v}" for k, v in d.items() if k not in ("name", "cad")]
    ))


@design.command("export")
@click.argument("name")
@click.argument("output_path", type=click.Path())
@click.pass_context
def design_export(ctx: click.Context, name: str, output_path: str) -> None:
    """Export a design JSON file to a path."""
    fmt = ctx.obj["fmt"]
    import shutil

    path = get_design_path(name)
    if path is None:
        fmt.error(f"Design '{name}' not found.")
        return

    shutil.copy2(path, output_path)
    result = {"name": name, "output": output_path, "status": "exported"}
    fmt.output(result, lambda d: f"Exported '{d['name']}' to {d['output']}")


@design.command("cad-spec")
@click.argument("component", required=False, type=click.Choice(["shaft", "casing", "blade"]))
@click.option("--set", "set_params", multiple=True, help="Set param as key=value (e.g. --set casing_thickness_to_inlet_radius=0.3)")
@click.option("--design", "design_name", default=None, help="Design name (uses active if omitted)")
@click.pass_context
def design_cad_spec(ctx: click.Context, component: str | None, set_params: tuple[str, ...], design_name: str | None) -> None:
    """View or set CAD specifications stored in a design.

    \b
    View all:          turbodesigner design cad-spec
    View component:    turbodesigner design cad-spec shaft
    Set values:        turbodesigner design cad-spec shaft --set stage_connect_screw_quantity=6

    \b
    Shaft params:
      stage_connect_length_to_heatset_thickness (default: 2.0)
      stage_connect_height_to_screw_head_diameter (default: 1.75)
      stage_connect_padding_to_attachment_height (default: 1.25)
      stage_connect_heatset_diameter_to_disk_height (default: 0.05)
      stage_connect_screw_quantity (default: 4)
      stage_connect_clearance (default: 0.5)

    \b
    Casing params:
      casing_thickness_to_inlet_radius (default: 0.25)
      stage_connect_height_to_screw_head_diameter (default: 1.75)
      stage_connect_padding_to_attachment_height (default: 1.25)
      stage_connect_heatset_diameter_to_disk_height (default: 0.25)
      stage_connect_screw_quantity (default: 4)
      half_connect_width_to_casing_thickness (default: 0.5)

    \b
    Blade params:
      screw_length_padding (default: 0.0)
      fastener_diameter_to_attachment_bottom_width (default: 0.25)
    """
    fmt = ctx.obj["fmt"]

    try:
        name, _ = resolve_design(design_name)
    except ValueError as e:
        fmt.error(str(e))

    if set_params and component:
        # Set mode: update spec values
        loaders = {"shaft": load_shaft_spec, "casing": load_casing_spec, "blade": load_blade_spec}
        spec = loaders[component](name)

        for param in set_params:
            if "=" not in param:
                fmt.error(f"Invalid format '{param}'. Use key=value (e.g. --set stage_connect_screw_quantity=6)")
            key, val = param.split("=", 1)
            if not hasattr(spec, key):
                fmt.error(f"Unknown parameter '{key}' for {component}. Run 'turbodesigner design cad-spec {component}' to see valid params.")
            # Type coercion
            current = getattr(spec, key)
            if isinstance(current, int):
                setattr(spec, key, int(val))
            elif isinstance(current, float):
                setattr(spec, key, float(val))
            elif isinstance(current, bool):
                setattr(spec, key, val.lower() in ("true", "1", "yes"))
            else:
                setattr(spec, key, val)

        save_cad_spec(name, component, spec)
        result = {"design": name, "component": component, "updated": {p.split("=")[0]: p.split("=")[1] for p in set_params}}
        fmt.output(result, lambda d: f"Updated {d['component']} spec for '{d['design']}': {d['updated']}")
    elif component:
        # View single component spec
        loaders = {"shaft": load_shaft_spec, "casing": load_casing_spec, "blade": load_blade_spec}
        spec = loaders[component](name)
        spec_dict = spec.model_dump()
        if fmt.use_json:
            fmt.output({"design": name, "component": component, "spec": spec_dict})
        else:
            click.echo(f"{component} spec for '{name}':")
            for k, v in spec_dict.items():
                click.echo(f"  {k}: {v}")
    else:
        # View all
        summary = get_cad_spec_summary(name)
        if fmt.use_json:
            fmt.output({"design": name, "cad": summary})
        else:
            if not summary:
                click.echo(f"No CAD specs stored for '{name}' (using defaults).")
                click.echo("Use 'turbodesigner design cad-spec <component> --set key=value' to customize.")
            else:
                click.echo(f"CAD specs for '{name}':")
                for comp, params in summary.items():
                    click.echo(f"  {comp}:")
                    for k, v in params.items():
                        click.echo(f"    {k}: {v}")


@design.command("report")
@click.option("--design", "design_name", default=None, help="Design name (uses active if omitted)")
@click.option("--no-open", is_flag=True, default=False, help="Don't open HTML in browser")
@click.pass_context
def design_report(ctx: click.Context, design_name: str | None, no_open: bool) -> None:
    """Generate an analysis report notebook, execute it, and open as HTML.

    \b
    Produces report.ipynb and report.html in the design's output/ folder.
    """
    fmt = ctx.obj["fmt"]

    try:
        name, design_path = resolve_design(design_name)
    except ValueError as e:
        fmt.error(str(e))
        return

    from turbodesigner.report import generate_report

    output_dir = str(design_path.parent / "output")
    html_path = generate_report(
        design_name=name,
        design_json_path=str(design_path),
        output_dir=output_dir,
        open_browser=not no_open,
    )

    result = {"design": name, "html": str(html_path), "notebook": str(html_path.with_suffix(".ipynb"))}
    fmt.output(result, lambda d: f"Report generated: {d['html']}")

