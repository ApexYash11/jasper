"""Shared Rich console rendering utilities for the Jasper CLI."""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from typing import Optional

console = Console()


def render_status(msg: str) -> None:
    """Print a styled Jasper status message."""
    console.print(f"[bold green]Jasper:[/bold green] {msg}")


def render_error(msg: str, hint: Optional[str] = None) -> None:
    """Print a styled error with an optional hint."""
    console.print(f"[bold red]✗ Error:[/bold red] {msg}")
    if hint:
        console.print(f"[dim]  Hint: {hint}[/dim]")


def render_warning(msg: str) -> None:
    """Print a styled warning."""
    console.print(f"[bold yellow]⚠  Warning:[/bold yellow] {msg}")


def render_success(msg: str) -> None:
    """Print a styled success message."""
    console.print(f"[bold green]✓[/bold green] {msg}")


def render_key_value_table(rows: list[tuple[str, str]], title: str = "") -> Table:
    """Build a two-column Rich Table from (key, value) tuples."""
    tbl = Table(box=box.SIMPLE, show_header=False, title=title or None)
    tbl.add_column(style="bold cyan", no_wrap=True)
    tbl.add_column(style="white")
    for key, value in rows:
        tbl.add_row(key, value)
    return tbl


def render_info_panel(content: str, title: str = "Info") -> Panel:
    """Wrap content in a styled panel for prominent display."""
    return Panel(Text(content), title=f"[bold]{title}[/bold]", border_style="blue")

