from typing import Any, Callable, Optional

import click
import json
import sys

from turbodesigner.cli.design import design
from turbodesigner.cli.analyze import analyze
from turbodesigner.cli.cad import cad


class JsonFormatter:
    """Context object that tracks --json flag for structured output."""
    def __init__(self, use_json: bool) -> None:
        self.use_json = use_json

    def output(self, data: Any, text_fn: Optional[Callable[[Any], str]] = None) -> None:
        """Output data as JSON or formatted text."""
        if self.use_json:
            click.echo(json.dumps(data, indent=2, default=str))
        elif text_fn:
            click.echo(text_fn(data))
        else:
            click.echo(data)

    def error(self, message: str, code: int = 1) -> None:
        """Output error and exit."""
        if self.use_json:
            click.echo(json.dumps({"error": message}), err=True)
        else:
            click.echo(f"Error: {message}", err=True)
        sys.exit(code)


from importlib.metadata import version, PackageNotFoundError

try:
    _version = version("turbodesigner")
except PackageNotFoundError:
    _version = "0.0.0"

BANNER = "\b\n" + fr"""  _____              _              ____              _
 |_   _|_   _  _ __ | |__    ___   |  _ \   ___  ___ (_)  __ _  _ __    ___  _ __
   | | | | | || '__|| '_ \  / _ \  | | | | / _ \/ __|| | / _` || '_ \  / _ \| '__|
   | | | |_| || |   | |_) || (_) | | |_| ||  __/\__ \| || (_| || | | ||  __/| |
   |_|  \__,_||_|   |_.__/  \___/  |____/  \___||___/|_| \__, ||_| |_| \___||_|
                                                         |___/
                         Turbomachinery Generation Framework
                              created by Open Orion, Inc.
                                      v{_version}
"""

HELP_TEXT = BANNER + """
\b
NOTE FOR AI AGENTS:
  - The --json flag goes HERE on the root command, not on subcommands.
    CORRECT: turbodesigner --json axial compressor analyze machine
    WRONG:   turbodesigner axial compressor analyze machine --json
  - Create designs with inline JSON (do NOT write temp files):
    turbodesigner axial compressor design create NAME --json '{...}'
  - During design iteration keep visualization ON (default) and use
    simple mode (default). Only use --complex for the final build.

\b
Quick start:
  turbodesigner axial compressor design create mark1 --json '{...}'
  turbodesigner axial compressor design use mark1
  turbodesigner --json axial compressor analyze stages
  turbodesigner axial compressor cad assembly
  turbodesigner axial compressor cad assembly --complex
"""


@click.group(context_settings={"max_content_width": 120}, help=HELP_TEXT)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON (for AI agents)")
@click.pass_context
def cli(ctx: click.Context, use_json: bool) -> None:
    """TurboDesigner CLI."""
    ctx.ensure_object(dict)
    ctx.obj["fmt"] = JsonFormatter(use_json)


@cli.group()
@click.pass_context
def axial(ctx: click.Context) -> None:
    """Axial turbomachinery (compressor, turbine, fan)."""
    pass


@axial.group()
@click.pass_context
def compressor(ctx: click.Context) -> None:
    """Axial compressor design, analysis, CAD, and export."""
    pass


compressor.add_command(design)
compressor.add_command(analyze)
compressor.add_command(cad)
