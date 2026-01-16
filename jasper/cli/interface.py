from datetime import datetime, timezone
import time
from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.markdown import Markdown
from rich.rule import Rule
from rich.tree import Tree
from rich import box
import re
from ..core.config import THEME, BANNER_ART
from ..core.state import FinalReport

def _fix_markdown_tables(text: str) -> str:
    """
    Ensures markdown tables have blank lines before and after them
    to assist the parser in identifying them correctly.
    """
    lines = text.split('\n')
    new_lines = []
    in_table = False
    
    for line in lines:
        is_table_line = line.strip().startswith('|')
        
        if is_table_line and not in_table:
            # Starting a table
            if new_lines and new_lines[-1].strip():
                new_lines.append('')
            in_table = True
        elif not is_table_line and in_table:
            # Ending a table
            if line.strip():
                new_lines.append('')
            in_table = False
            
        new_lines.append(line)
    return '\n'.join(new_lines)

def render_banner():
    """
    Renders the ASCII banner with a gradient, borderless.
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
    
    # Header construction without Panel
    header_group = Group(
        Text(""), # Top spacing
        Align.center(text),
        Align.center(subtitle),
        Text("") # Bottom spacing
    )
    
    return header_group

def render_mission_board(tasks, overall_status=""):
    """
    Renders the mission progress using a Live Tree structure.
    """
    tree = Tree(f"[bold {THEME['Brand']}] MISSION CONTROL[/bold {THEME['Brand']}]", guide_style="dim")
    
    # Status Phase with Animation
    if overall_status:
        style = f"bold {THEME['Accent']}"
        # Pulsing effect for the phase status
        if int(time.time() * 2) % 2 == 0:
            style = "bold white"
        tree.add(Text(overall_status, style=style))
    
    # Task List
    if tasks:
        task_tree = tree.add(f"[bold {THEME['Primary Text']}]RESEARCH PLAN[/bold {THEME['Primary Text']}]")
        for task in tasks:
            status = task.get("status", "pending")
            description = task.get("description", "")
            detail = task.get("detail", "")
            
            icon = "○"
            style = THEME["Primary Text"]
            
            if status == "running":
                # Shimmer effect for active task
                icon = "►"
                if int(time.time() * 5) % 2 == 0:
                    style = f"bold {THEME['Accent']}"
                else:
                    style = "bold white"
            elif status == "success":
                icon = "✔"
                style = f"bold {THEME['Success']}"
            elif status == "failed":
                icon = "✖"
                style = f"bold {THEME['Error']}"
            elif status == "pending":
                style = f"dim {THEME['Primary Text']}"

            node = task_tree.add(Text(f"{icon} {description}", style=style))
            
            if status == "running" and detail:
                node.add(Text(f"{detail}", style=f"italic {THEME['Accent']}"))
                
    return Panel(
        tree,
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
    
    # Body: Markdown with table fix
    fixed_body = _fix_markdown_tables(body_text)
    body = Markdown(fixed_body)
    
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
        border_style=THEME["Brand"],
        padding=(1, 2),
        expand=False,
        title="[bold]EXECUTIVE RESEARCH MEMO[/bold]",
        title_align="left"
    )
    
    return panel


def render_forensic_report(report: FinalReport):
    """
    Renders the v0.2.0 Forensic Artifact in the CLI.
    """
    # 1. Metadata Dashboard
    dash_table = Table(box=box.MINIMAL_DOUBLE_HEAD, show_header=False, expand=True, border_style=THEME["Brand"])
    dash_table.add_column("Label", style=f"bold {THEME['Accent']}")
    dash_table.add_column("Value", style="cyan")
    
    dash_table.add_row("QUERY HASH", report.query[:32] + "...") # Simplified hash for CLI
    dash_table.add_row("ENTITIES", ", ".join(report.tickers) or "N/A")
    dash_table.add_row("TIMESTAMP", report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"))
    dash_table.add_row("VERSION", f"v{report.version}")
    
    status_style = "bold green" if report.is_valid else "bold red"
    dash_table.add_row("VALIDATION", Text("PASSED" if report.is_valid else "FAILED", style=status_style))
    
    conf_style = "bold green" if report.confidence_score > 0.8 else "bold yellow"
    dash_table.add_row("CONFIDENCE", Text(f"{report.confidence_score:.2f}", style=conf_style))

    # 2. Evidence Matrix
    evidence_table = Table(title="[bold]1. EVIDENCE MATRIX[/bold]", box=box.ROUNDED, expand=True)
    evidence_table.add_column("ID", style="dim", width=6)
    evidence_table.add_column("Metric", style="white")
    evidence_table.add_column("Value", style="bold white")
    evidence_table.add_column("Source", style="dim")
    evidence_table.add_column("Status", style="green")

    for item in report.evidence_log:
        evidence_table.add_row(
            item.id, 
            item.metric, 
            str(item.value), 
            item.source, 
            item.status
        )

    # 3. Analysis Synthesis
    fixed_synthesis = _fix_markdown_tables(report.synthesis_text)
    synthesis_panel = Panel(
        Markdown(fixed_synthesis),
        title="[bold] ANALYSIS SYNTHESIS[/bold]",
        border_style=THEME["Accent"],
        padding=(1, 2)
    )

    # 4. Audit Trail (Mini)
    audit_table = Table(title="[bold]3. EXECUTION AUDIT TRAIL[/bold]", box=box.SIMPLE, expand=True)
    audit_table.add_column("Task", style="dim")
    audit_table.add_column("Tool", style="cyan")
    audit_table.add_column("Result", style="italic")

    if report.audit_trail:
        for task in report.audit_trail[-5:]: # Last 5 tasks
            audit_table.add_row(task.description[:40] + "...", task.tool, task.status)
    else:
        # Show message for qualitative analysis
        audit_table.add_row("[dim]No financial data tasks[/dim]", "[dim]N/A[/dim]", "[dim]Qualitative analysis[/dim]")

    return Group(
        Panel(dash_table, title="[bold]FORENSIC METADATA DASHBOARD[/bold]", border_style=THEME["Brand"]),
        evidence_table,
        synthesis_panel,
        audit_table,
        Rule(style="dim"),
        Text(f"Jasper v{report.version} | Deterministic Forensic Artifact", justify="center", style="dim")
    )
