"""Design report notebook generator.

Generates a Jupyter notebook (.ipynb) for a given design, executes it,
and converts to HTML for browser viewing.
"""
import json
import subprocess
import sys
from pathlib import Path


def _make_cell(cell_type: str, source: str | list[str], execution_count=None):
    """Create a notebook cell dict."""
    if isinstance(source, str):
        source = source.splitlines(keepends=True)
        if source and not source[-1].endswith("\n"):
            source[-1] += "\n"
    cell = {
        "cell_type": cell_type,
        "metadata": {},
        "source": source,
    }
    if cell_type == "code":
        cell["execution_count"] = execution_count
        cell["outputs"] = []
    return cell


def generate_report_notebook(design_name: str, design_json_path: str) -> dict:
    """Generate a notebook dict for a design analysis report."""
    cells = []

    # Title
    cells.append(_make_cell("markdown", f"# {design_name} — Design Analysis Report"))

    # Setup
    cells.append(_make_cell("code", f"""\
import json
from pathlib import Path
from turbodesigner.cli.state import TurboDesign
from turbodesigner.exporter import (
    machine_properties_df,
    dataclass_list_to_df,
    stages_flow_stations_df,
    stages_blade_rows_df,
    stages_blade_rows_streams_df,
    stages_blade_rows_sub_models_dfs,
)
from turbodesigner.visualizer import TurbomachineryVisualizer
import pandas as pd
import numpy as np

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 150)
pd.set_option('display.float_format', lambda x: '%.3f' % x)

design_path = Path({repr(design_json_path)})
with open(design_path) as f:
    export = TurboDesign.model_validate(json.load(f))
tm = export.definition
print(f"Loaded design: {design_name}")
print(f"Stages: {{len(tm.stages)}}")
"""))

    # Machine overview
    cells.append(_make_cell("markdown", "## Machine Overview"))
    cells.append(_make_cell("code", "machine_properties_df(tm)"))

    # Stage properties
    cells.append(_make_cell("markdown", "## Stage Properties"))
    cells.append(_make_cell("code", "dataclass_list_to_df(tm.stages)"))

    # Flow stations
    cells.append(_make_cell("markdown", "## Flow Station Properties"))
    cells.append(_make_cell("code", "stages_flow_stations_df(tm)"))

    # Annulus
    cells.append(_make_cell("markdown", "## Annulus Visualization"))
    cells.append(_make_cell("code", "TurbomachineryVisualizer.visualize_annulus(tm)"))

    # Blade rows scalar
    cells.append(_make_cell("markdown", "## Blade Row Properties (Scalars)"))
    cells.append(_make_cell("code", "stages_blade_rows_df(tm)"))

    # Blade rows streams
    cells.append(_make_cell("markdown", "## Blade Row Properties (Per-Stream)"))
    cells.append(_make_cell("code", "stages_blade_rows_streams_df(tm)"))

    # Sub-models
    cells.append(_make_cell("markdown", "## Sub-Model Analysis"))
    cells.append(_make_cell("code", """\
sub_dfs = stages_blade_rows_sub_models_dfs(tm)
for section_name, df in sub_dfs.items():
    display(pd.DataFrame({section_name: ["=" * 40]}))
    display(df)
"""))

    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12.0",
            },
        },
        "cells": cells,
    }
    return notebook


def generate_report(design_name: str, design_json_path: str, output_dir: str, open_browser: bool = True) -> Path:
    """Generate, execute, and convert a design report to HTML.

    Returns the path to the generated HTML file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    nb_path = output_path / "report.ipynb"
    html_path = output_path / "report.html"

    # Generate notebook
    notebook = generate_report_notebook(design_name, design_json_path)
    nb_path.write_text(json.dumps(notebook, indent=1))

    # Execute notebook
    subprocess.run(
        [
            sys.executable, "-m", "jupyter", "nbconvert",
            "--to", "notebook",
            "--execute",
            "--output", str(nb_path),
            str(nb_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    # Convert to HTML
    subprocess.run(
        [
            sys.executable, "-m", "jupyter", "nbconvert",
            "--to", "html",
            "--no-input",
            "--output", str(html_path),
            str(nb_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    if open_browser:
        _serve_and_open(html_path)

    return html_path


def _serve_and_open(html_path: Path):
    """Serve the HTML file on a local port and open in browser."""
    import os
    import threading
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    directory = str(html_path.parent)
    filename = html_path.name

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, format, *args):
            pass  # silence logs

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/{filename}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    browser = os.environ.get("BROWSER", "")
    if browser:
        subprocess.run([browser, url])
    else:
        import webbrowser
        webbrowser.open(url)

    # Keep server alive briefly so the browser can fetch the file
    import time
    time.sleep(3)
    server.shutdown()
