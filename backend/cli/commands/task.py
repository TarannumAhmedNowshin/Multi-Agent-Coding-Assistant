"""CLI command: submit and run a developer task through the agent workflow."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from backend.graph.workflow import run_task

app = typer.Typer(no_args_is_help=True)
console = Console()


def _render_state(state: dict) -> Table:
    """Build a Rich table summarising the final workflow state."""
    table = Table(title="Task Result", show_header=True, header_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    status = state.get("status", "unknown")
    status_color = {"completed": "green", "failed": "red"}.get(status, "yellow")
    table.add_row("Task ID", state.get("task_id", "—"))
    table.add_row("Status", f"[{status_color}]{status}[/{status_color}]")
    table.add_row("Total Tokens", str(state.get("total_tokens", 0)))

    steps = state.get("steps", [])
    table.add_row("Steps Planned", str(len(steps)))
    table.add_row("Steps Completed", str(state.get("current_step_index", 0)))

    if state.get("result_summary"):
        table.add_row("Summary", state["result_summary"][:300])

    errors = state.get("errors", [])
    if errors:
        table.add_row("Errors", f"[red]{len(errors)} error(s)[/red]")

    return table


def _display_artifacts(state: dict) -> None:
    """Print generated code artifacts with syntax highlighting."""
    artifacts = state.get("code_artifacts", [])
    if not artifacts:
        return

    console.print()
    console.rule("[bold cyan]Generated Code Artifacts[/bold cyan]")
    for art in artifacts:
        lang = art.get("language", "text") or "text"
        file_path = art.get("file_path", "untitled")
        content = art.get("content", "")
        console.print(f"\n[bold green]{file_path}[/bold green]")
        console.print(Syntax(content, lang, theme="monokai", line_numbers=True))


def _display_errors(state: dict) -> None:
    """Print errors if any occurred."""
    errors = state.get("errors", [])
    if not errors:
        return

    console.print()
    console.rule("[bold red]Errors[/bold red]")
    for i, err in enumerate(errors, 1):
        console.print(f"  [red]{i}.[/red] {err}")


async def _run_task(description: str, project_id: Optional[str]) -> None:
    """Run the agent workflow and display live progress."""
    console.print(
        Panel(
            f"[bold]Task:[/bold] {description}"
            + (f"\n[bold]Project:[/bold] {project_id}" if project_id else ""),
            title="[cyan]Starting Agent Workflow[/cyan]",
            border_style="cyan",
        )
    )

    with console.status("[bold cyan]Agents are working…[/bold cyan]", spinner="dots"):
        final_state = await run_task(
            task_description=description,
            project_id=project_id,
        )

    # Display results
    console.print()
    console.print(_render_state(final_state))
    _display_artifacts(final_state)
    _display_errors(final_state)

    # Steps detail
    steps = final_state.get("steps", [])
    if steps:
        console.print()
        console.rule("[bold cyan]Plan Steps[/bold cyan]")
        step_table = Table(show_header=True, header_style="bold")
        step_table.add_column("#", style="dim", width=4)
        step_table.add_column("Title")
        step_table.add_column("Description", max_width=60)
        for i, step in enumerate(steps, 1):
            completed_idx = final_state.get("current_step_index", 0)
            marker = "[green]✓[/green]" if i <= completed_idx else "[dim]○[/dim]"
            step_table.add_row(
                f"{marker} {i}",
                step.get("title", "—"),
                step.get("description", "—")[:60],
            )
        console.print(step_table)

    status = final_state.get("status", "unknown")
    if status == "completed":
        console.print("\n[bold green]✓ Task completed successfully![/bold green]")
    elif status == "failed":
        console.print("\n[bold red]✗ Task failed.[/bold red]")
    else:
        console.print(f"\n[bold yellow]Task ended with status: {status}[/bold yellow]")


@app.command("run")
def run(
    description: str = typer.Argument(..., help="Natural-language task description."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project UUID to scope context retrieval."),
) -> None:
    """Submit a task and run the full agent workflow."""
    asyncio.run(_run_task(description, project))
