"""CLI command: display task progress and results."""

import asyncio
import uuid as _uuid
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.database.engine import async_session_factory
from backend.database.models import CodeArtifact, Step, Task

app = typer.Typer(no_args_is_help=True)
console = Console()


async def _fetch_task(task_id: _uuid.UUID) -> dict | None:
    """Load a task with its steps and code artifacts from the database."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.steps).selectinload(Step.code_artifacts),
            )
        )
        task = result.scalar_one_or_none()
        if task is None:
            return None

        return {
            "id": str(task.id),
            "description": task.description,
            "status": task.status.value if task.status else "unknown",
            "result_summary": task.result_summary,
            "total_tokens": task.total_tokens or 0,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "steps": [
                {
                    "order": s.order,
                    "title": s.title,
                    "description": s.description,
                    "status": s.status.value if s.status else "unknown",
                    "retry_count": s.retry_count or 0,
                    "artifacts": [
                        {
                            "file_path": a.file_path,
                            "content": a.content,
                            "language": a.language,
                            "version": a.version,
                        }
                        for a in sorted(
                            s.code_artifacts, key=lambda a: a.version
                        )
                    ],
                }
                for s in sorted(task.steps, key=lambda s: s.order)
            ],
        }


async def _list_tasks(limit: int) -> list[dict]:
    """Fetch the most recent tasks."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Task).order_by(Task.created_at.desc()).limit(limit)
        )
        tasks = result.scalars().all()
        return [
            {
                "id": str(t.id),
                "description": t.description[:80],
                "status": t.status.value if t.status else "unknown",
                "tokens": t.total_tokens or 0,
                "created": t.created_at,
            }
            for t in tasks
        ]


def _status_color(status: str) -> str:
    return {
        "completed": "green",
        "passed": "green",
        "failed": "red",
        "pending": "dim",
        "in_progress": "cyan",
        "generating": "cyan",
        "reviewing": "yellow",
        "executing": "magenta",
    }.get(status, "white")


def _display_task(data: dict) -> None:
    """Render a rich view of a single task."""
    status = data["status"]
    sc = _status_color(status)

    console.print(
        Panel(
            f"[bold]Description:[/bold] {data['description']}\n"
            f"[bold]Status:[/bold]      [{sc}]{status}[/{sc}]\n"
            f"[bold]Tokens:[/bold]      {data['total_tokens']}\n"
            f"[bold]Created:[/bold]     {data['created_at']}\n"
            f"[bold]Updated:[/bold]     {data['updated_at']}",
            title=f"[cyan]Task {data['id']}[/cyan]",
            border_style="cyan",
        )
    )

    if data.get("result_summary"):
        console.print(
            Panel(data["result_summary"], title="[green]Result Summary[/green]", border_style="green")
        )

    # Steps table
    steps = data.get("steps", [])
    if steps:
        table = Table(title="Steps", show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title")
        table.add_column("Status", width=12)
        table.add_column("Retries", width=8, justify="center")
        table.add_column("Artifacts", width=10, justify="center")

        for s in steps:
            s_sc = _status_color(s["status"])
            table.add_row(
                str(s["order"]),
                s["title"],
                f"[{s_sc}]{s['status']}[/{s_sc}]",
                str(s["retry_count"]),
                str(len(s.get("artifacts", []))),
            )
        console.print(table)

    # Code artifacts
    for s in steps:
        for art in s.get("artifacts", []):
            lang = art.get("language") or "text"
            console.print(f"\n[bold green]{art['file_path']}[/bold green] (v{art['version']})")
            console.print(Syntax(art["content"], lang, theme="monokai", line_numbers=True))


async def _show_status(task_id_str: str, show_code: bool) -> None:
    """Fetch and display a task's status."""
    try:
        task_id = _uuid.UUID(task_id_str)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid UUID: {task_id_str}")
        raise typer.Exit(code=1)

    data = await _fetch_task(task_id)
    if data is None:
        console.print(f"[red]Error:[/red] Task not found: {task_id}")
        raise typer.Exit(code=1)

    if not show_code:
        # Strip artifact content to keep output compact
        for s in data.get("steps", []):
            s["artifacts"] = []

    _display_task(data)


async def _show_list(limit: int) -> None:
    """List recent tasks."""
    tasks = await _list_tasks(limit)
    if not tasks:
        console.print("[dim]No tasks found.[/dim]")
        return

    table = Table(title="Recent Tasks", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", max_width=36)
    table.add_column("Description", max_width=60)
    table.add_column("Status", width=14)
    table.add_column("Tokens", justify="right", width=8)
    table.add_column("Created")

    for t in tasks:
        sc = _status_color(t["status"])
        table.add_row(
            t["id"],
            t["description"],
            f"[{sc}]{t['status']}[/{sc}]",
            str(t["tokens"]),
            str(t["created"]),
        )
    console.print(table)


@app.callback(invoke_without_command=True)
def status(
    task_id: Optional[str] = typer.Argument(None, help="Task UUID to inspect. Omit to list recent tasks."),
    code: bool = typer.Option(False, "--code", "-c", help="Show generated code artifacts."),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of recent tasks to list (when no ID given)."),
) -> None:
    """Display the status of a task, or list recent tasks."""
    if task_id:
        asyncio.run(_show_status(task_id, show_code=code))
    else:
        asyncio.run(_show_list(limit))
