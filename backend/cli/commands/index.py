"""CLI command: index a codebase directory into FAISS."""

import asyncio
import uuid
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from backend.database.engine import async_session_factory
from backend.database.models import Project
from backend.vectordb.indexer import Indexer

app = typer.Typer(no_args_is_help=True)
console = Console()


async def _create_project(name: str, root_path: str) -> uuid.UUID:
    """Create a Project row in the database and return its UUID."""
    async with async_session_factory() as session:
        project = Project(name=name, root_path=root_path)
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project.id


async def _run_index(directory: str, project_name: Optional[str]) -> None:
    """Orchestrate codebase indexing with Rich progress output."""
    from pathlib import Path

    root = Path(directory).resolve()
    if not root.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {root}")
        raise typer.Exit(code=1)

    name = project_name or root.name

    # Create project in DB
    with console.status("[bold cyan]Creating project record…[/bold cyan]"):
        project_id = await _create_project(name, str(root))

    console.print(
        Panel(
            f"[bold]Project:[/bold] {name}\n"
            f"[bold]Path:[/bold]    {root}\n"
            f"[bold]ID:[/bold]      {project_id}",
            title="[green]Project Created[/green]",
            border_style="green",
        )
    )

    # Index the directory
    indexer = Indexer()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Indexing codebase…", total=None)

        async with async_session_factory() as session:
            store = await indexer.index_directory(
                root, project_id=project_id, db_session=session,
            )
            await session.commit()

        progress.update(task, completed=100, total=100)

    console.print(
        Panel(
            f"[bold]Vectors stored:[/bold] {store.size}\n"
            f"[bold]Index location:[/bold] .index_store/{project_id}/",
            title="[green]Indexing Complete[/green]",
            border_style="green",
        )
    )


@app.callback(invoke_without_command=True)
def index(
    directory: str = typer.Argument(..., help="Path to the directory to index."),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Project name (defaults to directory name)."),
) -> None:
    """Index a codebase directory for RAG-powered context retrieval."""
    asyncio.run(_run_index(directory, name))
