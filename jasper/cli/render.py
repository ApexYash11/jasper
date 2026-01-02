from rich.console import Console

console = Console()

def render_status(msg: str) -> None:
    console.print(f"[bold green]Jasper:[/bold green] {msg}")
