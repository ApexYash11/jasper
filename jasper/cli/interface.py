from datetime import datetime, timezone
from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.markdown import Markdown
from rich.rule import Rule
from rich import box
from ..core.config import THEME, BANNER_ART

def render_banner():
    """
    Renders the ASCII banner with a gradient and subtitle.
    """
    # Create Text object from raw ASCII
    text = Text(BANNER_ART)
    
    # Apply Gradient
    # Characters 0-60: Bold White
    text.stylize("bold white", 0, 60)
    # Characters 60-200: Bold Accent
    text.stylize(f"bold {THEME['Accent']}", 60, 200)
    # Characters 200+: Bold Brand
    text.stylize(f"bold {THEME['Brand']}", 200)
    
    # Subtitle with background color
    subtitle = Text(" >> FINANCIAL INTELLIGENCE SYSTEM << ", style=f"bold #000000 on {THEME['Accent']}")
    
    # Panel with padding and breathing room
    panel = Panel(
        Align.center(text),
        padding=(2, 4),
        subtitle=subtitle,
        subtitle_align="center",
        border_style=THEME["Brand"],
        style=f"on {THEME['Background']}"
    )
    return panel

def render_mission_board(tasks):
    """
    Renders the list of tasks with status icons.
    """
    lines = []
    for task in tasks:
        status = task.get("status", "pending")
        description = task.get("description", "")
        detail = task.get("detail", "")
        
        icon = "○"
        style = THEME["Primary Text"]
        
        if status == "running":
            icon = "►"
            style = f"bold {THEME['Accent']}"
        elif status == "success":
            icon = "✔"
            style = f"bold {THEME['Success']}"
        elif status == "failed":
            icon = "✖"
            style = f"bold {THEME['Error']}"
        elif status == "pending":
            style = f"dim {THEME['Primary Text']}"

        lines.append(Text(f"{icon} {description}", style=style))
        
        # Show sub-step detail for running tasks
        if status == "running" and detail:
            lines.append(Text(f"  └─ {detail}", style=f"italic {THEME['Accent']}"))
            
    # Join lines with newlines
    content = Text("\n").join(lines) if lines else Text("No active tasks.")
    
    return Panel(
        content,
        title="[bold]MISSION CONTROL[/bold]",
        border_style=THEME["Brand"],
        padding=(1, 2),
        style=f"on {THEME['Background']}"
    )

def render_final_report(body_text, tickers, sources):
    """
    Renders the final intelligence report in an executive memo style.
    """
    # Header Construction
    header_rows = []
    
    # Row 1: INTELLIGENCE MEMO
    header_rows.append(Text("INTELLIGENCE MEMO", style="bold white"))
    
    # Row 2: Target Entities
    target_labels = Text("Target Entities: ", style="dim grey50")
    target_values = Text(", ".join(tickers), style="bold white")
    header_rows.append(target_labels + target_values)
    
    # Row 3: Data As Of | Sources
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    date_label = Text("Data As Of: ", style="dim grey50")
    date_value = Text(current_date, style="bold white")
    source_label = Text(" | Sources: ", style="dim grey50")
    source_value = Text(", ".join(sources), style="bold white")
    header_rows.append(date_label + date_value + source_label + source_value)
    
    # Group header and add a separator
    header_group = Group(*header_rows)
    separator = Rule(style="dim")
    
    # Body: Markdown
    body = Markdown(body_text)
    
    # Combine everything into a Group
    content_group = Group(
        header_group,
        separator,
        Text(""), # Padding
        body
    )
    
    # Main Container Panel
    panel = Panel(
        content_group,
        border_style="green",
        padding=(1, 2),
        expand=False
    )
    
    return panel
