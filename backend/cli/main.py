"""Typer CLI application — the developer-facing entry point.

Usage::

    python -m backend.cli.main --help
    python -m backend.cli.main index ./my_project
    python -m backend.cli.main task run "Add JWT auth"
    python -m backend.cli.main status <task-id>
"""

import typer

from backend.cli.commands.index import app as index_app
from backend.cli.commands.status import app as status_app
from backend.cli.commands.task import app as task_app
from backend.utils.logger import setup_logging

app = typer.Typer(
    name="agentic",
    help="Agentic Developer — multi-agent AI coding assistant.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(index_app, name="index", help="Index a codebase into the FAISS vector store.")
app.add_typer(task_app, name="task", help="Create and run developer tasks.")
app.add_typer(status_app, name="status", help="Check task progress and results.")


@app.callback()
def _startup() -> None:
    """Initialise logging on every CLI invocation."""
    setup_logging()


if __name__ == "__main__":
    app()
