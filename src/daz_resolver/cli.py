"""JSON-first command-line automation using the shared engine."""

import json
from pathlib import Path
from typing import Annotated

import typer

from .discovery import discover as detect
from .discovery import selected_paths
from .engine import Plan, make_plan
from .index import index_sources
from .install import install as execute
from .install import recover as recover_library

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def emit(value):
    typer.echo(json.dumps(value, indent=2))


def pairs(values: list[str]) -> dict[str, str]:
    result = {}
    for value in values:
        if "=" not in value:
            raise typer.BadParameter("Expected relative/path=value")
        name, choice = value.rsplit("=", 1)
        result[name] = choice
    return result


@app.command()
def discover():
    """Inspect local DIM profiles and supported Studio settings (read-only)."""
    emit(detect())


@app.command()
def plan(
    source: Annotated[list[Path] | None, typer.Option()] = None,
    library: Annotated[list[Path] | None, typer.Option()] = None,
    scene: Annotated[list[Path] | None, typer.Option()] = None,
    product_root: Annotated[list[Path] | None, typer.Option()] = None,
    destination: Annotated[Path | None, typer.Option()] = None,
    output: Annotated[Path | None, typer.Option()] = None,
    choose: Annotated[list[str] | None, typer.Option()] = None,
    conflict: Annotated[list[str] | None, typer.Option()] = None,
    detected: bool = False,
    profile: str | None = None,
    studio: str | None = None,
):
    """Index sources and produce a read-only whole-product install plan."""
    sources, libraries = list(source or []), list(library or [])
    try:
        if detected:
            auto_sources, auto_libraries = selected_paths(detect(), profile, studio)
            sources = sources or auto_sources
            libraries = libraries or auto_libraries
        if not sources:
            raise ValueError("At least one --source or detected archive folder is required")
        result = make_plan(
            index_sources(sources, product_root),
            destination,
            scene,
            libraries,
            pairs(choose or []),
            pairs(conflict or []),
        ).to_dict()
        result["configuration"] = {
            "sources": [
                {"path": str(p), "provenance": "user" if source else "detected"} for p in sources
            ],
            "libraries": [
                {"path": str(p), "provenance": "user" if library else "detected"} for p in libraries
            ],
            "destination": {
                "path": str(destination) if destination else None,
                "provenance": "user",
            },
        }
        if output:
            # Do not let an output option overwrite a content/source/scene file.
            resolved = output.resolve()
            protected = (
                sources + libraries + list(scene or []) + ([destination] if destination else [])
            )
            if any(
                resolved == p.resolve() or resolved.is_relative_to(p.resolve()) for p in protected
            ):
                raise ValueError("Plan output must be outside source, scene and library paths")
            output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        emit(result)
    except (ValueError, OSError) as exc:
        emit({"error": str(exc)})
        raise typer.Exit(1) from exc


@app.command()
def install(plan_file: Path, dry_run: bool = False):
    """Validate and install a reviewed JSON plan; explicit destination required in plan."""
    try:
        result = Plan.from_dict(json.loads(plan_file.read_text(encoding="utf-8")))
        emit(result.to_dict() if dry_run else execute(result))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        emit({"error": str(exc)})
        raise typer.Exit(1) from exc


@app.command()
def recover(destination: Path):
    """Conservatively roll back interrupted tool transactions in this library."""
    try:
        emit(recover_library(destination))
    except (ValueError, OSError, KeyError) as exc:
        emit({"error": str(exc)})
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    app()
