from datetime import datetime, timezone
import time
import hashlib
import re
from typing import Optional
from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.markdown import Markdown
from rich.rule import Rule
from rich.tree import Tree
from rich import box
from ..core.config import THEME, BANNER_ART
from ..core.state import FinalReport


_BOX_CHARS = {
    "top_left": "┌",
    "top_right": "┐",
    "bottom_left": "└",
    "bottom_right": "┘",
    "horizontal": "─",
    "vertical": "│",
    "top_t": "┬",
    "bottom_t": "┴",
    "left_t": "├",
    "right_t": "┤",
    "cross": "┼",
}


def _is_numeric_cell(value: str) -> bool:
    """Return True if a cell looks numeric (for right alignment)."""
    trimmed = value.strip()
    return bool(re.match(r"^[$]?[-+]?[\d,]+\.?\d*[%BMKx]?$", trimmed))


def _parse_markdown_table(table_text: str) -> Optional[dict]:
    """Parse a markdown table block into headers and rows."""
    lines = [line.strip() for line in table_text.strip().split("\n") if line.strip()]
    if len(lines) < 2:
        return None

    header_line = lines[0]
    if "|" not in header_line:
        return None

    headers = [cell.strip() for cell in header_line.split("|")]
    if headers and headers[0] == "":
        headers = headers[1:]
    if headers and headers[-1] == "":
        headers = headers[:-1]
    if not headers:
        return None

    separator_line = lines[1]
    if not re.match(r"^[\s|:-]+$", separator_line):
        return None

    rows = []
    for line in lines[2:]:
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        if cells:
            rows.append(cells)

    if not rows:
        return None

    return {"headers": headers, "rows": rows}


def _render_box_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render parsed table as a compact unicode box table."""
    col_widths = [len(header) for header in headers]
    for row in rows:
        for idx in range(min(len(row), len(col_widths))):
            col_widths[idx] = max(col_widths[idx], len(row[idx]))

    align_right = []
    for col_idx in range(len(headers)):
        numeric_count = 0
        for row in rows:
            if col_idx < len(row) and _is_numeric_cell(row[col_idx]):
                numeric_count += 1
        align_right.append(numeric_count > len(rows) / 2)

    def pad_cell(value: str, width: int, right: bool) -> str:
        return value.rjust(width) if right else value.ljust(width)

    top = (
        _BOX_CHARS["top_left"]
        + _BOX_CHARS["top_t"].join(_BOX_CHARS["horizontal"] * (width + 2) for width in col_widths)
        + _BOX_CHARS["top_right"]
    )
    header_row = (
        _BOX_CHARS["vertical"]
        + _BOX_CHARS["vertical"].join(
            f" {pad_cell(header, col_widths[idx], False)} " for idx, header in enumerate(headers)
        )
        + _BOX_CHARS["vertical"]
    )
    header_sep = (
        _BOX_CHARS["left_t"]
        + _BOX_CHARS["cross"].join(_BOX_CHARS["horizontal"] * (width + 2) for width in col_widths)
        + _BOX_CHARS["right_t"]
    )

    data_rows = []
    for row in rows:
        padded = row + [""] * (len(headers) - len(row))
        data_rows.append(
            _BOX_CHARS["vertical"]
            + _BOX_CHARS["vertical"].join(
                f" {pad_cell(padded[idx], col_widths[idx], align_right[idx])} " for idx in range(len(headers))
            )
            + _BOX_CHARS["vertical"]
        )

    bottom = (
        _BOX_CHARS["bottom_left"]
        + _BOX_CHARS["bottom_t"].join(_BOX_CHARS["horizontal"] * (width + 2) for width in col_widths)
        + _BOX_CHARS["bottom_right"]
    )

    return "\n".join([top, header_row, header_sep, *data_rows, bottom])


def _transform_markdown_tables_to_box(text: str) -> str:
    """Transform markdown tables in text to unicode box tables."""
    normalized = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n"))

    table_regex = re.compile(r"^(\|[^\n]+\|\n\|[-:| \t]+\|(?:\n\|[^\n]+\|)*)", re.MULTILINE)
    table_regex_alt = re.compile(r"^([^\n|]*\|[^\n]+\n[-:| \t]+(?:\n[^\n|]*\|[^\n]+)*)", re.MULTILINE)

    def replace_table(match: re.Match) -> str:
        candidate = match.group(0)
        parsed = _parse_markdown_table(candidate)
        if not parsed:
            return candidate
        rendered = _render_box_table(parsed["headers"], parsed["rows"])
        return f"\n```text\n{rendered}\n```\n"

    transformed = table_regex.sub(replace_table, normalized)

    def replace_alt(match: re.Match) -> str:
        candidate = match.group(0)
        if _BOX_CHARS["top_left"] in candidate:
            return candidate
        parsed = _parse_markdown_table(candidate)
        if not parsed:
            return candidate
        rendered = _render_box_table(parsed["headers"], parsed["rows"])
        return f"\n```text\n{rendered}\n```\n"

    return table_regex_alt.sub(replace_alt, transformed)


def _format_cli_markdown(text: str) -> str:
    """Normalize markdown tables then render them as box tables for CLI readability."""
    return _transform_markdown_tables_to_box(_compact_cli_layout(_fix_markdown_tables(text)))


def _compact_cli_layout(text: str) -> str:
    """Tighten report layout for terminal readability while preserving code/table blocks."""
    lines = text.replace("\r\n", "\n").split("\n")
    compact_lines = []
    in_code_block = False

    for raw in lines:
        line = raw.rstrip()

        # Preserve fenced blocks as-is (used for rendered box tables)
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            compact_lines.append(line)
            continue

        if in_code_block:
            compact_lines.append(line)
            continue

        stripped = line.strip()

        # Drop obvious visual noise rows emitted by some model outputs
        if stripped in {".", "•"}:
            continue

        # Normalize warning lines to markdown sub-headings
        if stripped.startswith("⚠️ WARNING:") and not stripped.startswith("###"):
            compact_lines.append(f"### {stripped}")
            continue

        compact_lines.append(line)

    # Collapse 3+ blank lines to at most one blank line outside fenced blocks
    output = []
    in_code_block = False
    blank_count = 0

    for line in compact_lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            output.append(line)
            blank_count = 0
            continue

        if in_code_block:
            output.append(line)
            continue

        if line.strip() == "":
            blank_count += 1
            if blank_count <= 1:
                output.append("")
            continue

        blank_count = 0
        output.append(line)

    return "\n".join(output).strip()

def _fix_markdown_tables(text: str) -> str:
    """
    Parse and reconstruct markdown tables, handling financial data specially.
    
    Two-pass approach:
    - Pass 1: Normalize financial values ($, %, K/M/B suffixes)
    - Pass 2: Validate table structure and fix compressed rows
    """
    lines = text.split('\n')
    result = []
    num_columns = None
    in_table = False
    in_incomplete_table = False
    table_buffer = []
    
    # Regex for financial data: $1.2B, $1,234.56, 45.2%, etc.
    
    for line_idx, line in enumerate(lines):
        if not line.strip().startswith('|'):
            # Check if we were in a table
            if in_table:
                # Try to process the table buffer
                if num_columns:
                    table_lines = _parse_financial_table(table_buffer, num_columns)
                    result.extend(table_lines.split('\n') if table_lines else [])
                else:
                    # No columns detected, just pass through
                    for row_type, cells in table_buffer:
                        result.append('| ' + ' | '.join(cells) + ' |')
                in_table = False

                table_buffer = []
                num_columns = None
            result.append(line)
            continue
        
        # We're in a table row
        in_table = True
        stripped = line.strip()
        
        # Split by pipes and normalize cells
        parts = stripped.split('|')
        cells = [_normalize_cell(c.strip()) for c in parts if c.strip()]
        
        if not cells:
            continue
        
        # Detect separator row
        if all(re.match(r'^:?-+:?$', c) for c in cells):
            if num_columns is None:
                num_columns = len(cells)
            table_buffer.append(('separator', cells))
            continue
        
        # This is a data row
        if num_columns is None:
            num_columns = len(cells)  # Use first data row to establish column count
        
        table_buffer.append(('data', cells))
    
    # Process any remaining table
    if in_table and table_buffer:
        if num_columns:
            table_lines = _parse_financial_table(table_buffer, num_columns)
            result.extend(table_lines.split('\n') if table_lines else [])
        else:
            for row_type, cells in table_buffer:
                result.append('| ' + ' | '.join(cells) + ' |')
    
    return '\n'.join(result)


def _normalize_cell(cell: str) -> str:
    """Normalize a table cell, preserving financial formatting."""
    if not cell:
        return cell
    
    # Preserve financial patterns but clean up spacing
    # Don't break up numbers/percentages/currencies
    return cell.strip()


def _parse_financial_table(table_buffer: list, num_columns: int) -> str:
    """
    Parse a table buffer with rows grouped by type (separator/data).
    Handles financial data formatting and reconstructs compressed rows.
    """
    if not table_buffer or num_columns is None or num_columns < 2:
        return ""
    
    result = []
    rows_to_emit = []
    
    for row_type, cells in table_buffer:
        if row_type == 'separator':
            # Emit any pending data rows first
            if rows_to_emit:
                result.extend(rows_to_emit)
                rows_to_emit = []
            # Emit the separator
            result.append('| ' + ' | '.join(['---'] * num_columns) + ' |')
        else:
            # Data row - may need to be split if it was compressed
            if len(cells) == num_columns:
                # Perfect fit
                result.append('| ' + ' | '.join(cells) + ' |')
            elif len(cells) > num_columns and len(cells) % num_columns == 0:
                # Multiple complete rows compressed together
                for i in range(0, len(cells), num_columns):
                    chunk = cells[i:i + num_columns]
                    result.append('| ' + ' | '.join(chunk) + ' |')
            elif len(cells) > num_columns:
                # Partial compression - try to reasonably split
                # Take first num_columns as one row, rest as next
                for i in range(0, len(cells), num_columns):
                    chunk = cells[i:i + num_columns]
                    if len(chunk) < num_columns:
                        chunk.extend([''] * (num_columns - len(chunk)))
                    result.append('| ' + ' | '.join(chunk) + ' |')
            else:
                # Fewer cells than columns - pad it
                cells_padded = cells + [''] * (num_columns - len(cells))
                result.append('| ' + ' | '.join(cells_padded) + ' |')
    
    return '\n'.join(result)

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

def build_persistent_board():
    """
    Build a persistent mission board tree that NEVER gets rebuilt.
    Returns a tuple: (root_panel, planning_node, execution_node, synthesis_node)
    
    Each node can be appended to independently without rebuilding the entire tree.
    """
    root_tree = Tree(f"[bold {THEME['Brand']}] MISSION CONTROL[/bold {THEME['Brand']}]", guide_style="dim")
    
    # Create three phase sections (persistent tree nodes)
    planning_node = root_tree.add(f"[bold {THEME['Accent']}]▸ PLANNING[/bold {THEME['Accent']}]")
    execution_node = root_tree.add(f"[bold {THEME['Accent']}]▸ EXECUTION[/bold {THEME['Accent']}]")
    synthesis_node = root_tree.add(f"[bold {THEME['Accent']}]▸ SYNTHESIS[/bold {THEME['Accent']}]")
    
    # Create the panel (wraps the tree)
    root_panel = Panel(
        root_tree,
        border_style=THEME["Brand"],
        padding=(1, 2),
        style=f"on {THEME['Background']}"
    )
    
    return (root_panel, planning_node, execution_node, synthesis_node)


def update_phase_node(phase_node, status_text: str = "", tasks=None):
    """
    Update a phase node with status and tasks.
    ONLY called during initialization or when we need to reset a phase.
    During normal updates, use append_task_to_node() instead.
    """
    if tasks is None:
        tasks = []
    
    # Clear existing children properly using while loop to avoid modification during iteration
    while phase_node.children:
        phase_node.children.pop()
    
    # Add status line if provided - use plain string (Tree will render it as text)
    if status_text:
        phase_node.add(status_text)
    
    # Add task nodes if provided
    if tasks:
        for task in tasks:
            status = task.get("status", "pending")
            description = task.get("description", "")
            
            icon = "○"
            
            if status == "running":
                icon = "►"
            elif status == "success":
                icon = "✔"
            elif status == "failed":
                icon = "✖"
            
            phase_node.add(f"{icon} {description}")


def append_task_to_node(phase_node, task_description: str, status: str = "pending"):
    """
    Append a single task to a phase node WITHOUT clearing existing content.
    This is used during normal execution to add tasks one by one.
    """
    icon = "○"
    
    if status == "running":
        icon = "►"
    elif status == "success":
        icon = "✔"
    elif status == "failed":
        icon = "✖"
    
    phase_node.add(f"{icon} {task_description}")


def update_synthesis_status(synthesis_node, status_text: str):
    """
    Update the synthesis node with real-time streaming status.
    Maintains a simple status line at root level.
    """
    # For synthesis, we just clear and re-add the status line
    # This keeps it simple and avoids complex Tree manipulation
    while synthesis_node.children:
        synthesis_node.children.pop()
    
    synthesis_node.add(status_text)


def render_mission_board(planning_tasks=None, planning_status="", execution_tasks=None, execution_status="", synthesis_status=""):
    """
    Renders the mission progress with phases grouped: PLANNING → EXECUTION → SYNTHESIS
    """
    if planning_tasks is None:
        planning_tasks = []
    if execution_tasks is None:
        execution_tasks = []
        
    tree = Tree(f"[bold {THEME['Brand']}] MISSION CONTROL[/bold {THEME['Brand']}]", guide_style="dim")
    
    # === PLANNING PHASE ===
    if planning_status or planning_tasks:
        planning_tree = tree.add(f"[bold {THEME['Accent']}]▸ PLANNING[/bold {THEME['Accent']}]")
        if planning_status:
            planning_tree.add(Text(planning_status, style="bold white"))
        
        for task in planning_tasks:
            status = task.get("status", "pending")
            description = task.get("description", "")
            detail = task.get("detail", "")
            
            icon = "○"
            style = THEME["Primary Text"]
            
            if status == "running":
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

            node = planning_tree.add(Text(f"{icon} {description}", style=style))
            if status == "running" and detail:
                node.add(Text(f"{detail}", style=f"italic {THEME['Accent']}"))
    
    # === EXECUTION PHASE ===
    if execution_status or execution_tasks:
        execution_tree = tree.add(f"[bold {THEME['Accent']}]▸ EXECUTION[/bold {THEME['Accent']}]")
        if execution_status:
            execution_tree.add(Text(execution_status, style="bold white"))
        
        for task in execution_tasks:
            status = task.get("status", "pending")
            description = task.get("description", "")
            detail = task.get("detail", "")
            
            icon = "○"
            style = THEME["Primary Text"]
            
            if status == "running":
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

            node = execution_tree.add(Text(f"{icon} {description}", style=style))
            if status == "running" and detail:
                node.add(Text(f"{detail}", style=f"italic {THEME['Accent']}"))
    
    # === SYNTHESIS PHASE ===
    if synthesis_status:
        synthesis_tree = tree.add(f"[bold {THEME['Accent']}]▸ SYNTHESIS[/bold {THEME['Accent']}]")
        synthesis_tree.add(Text(synthesis_status, style="bold white"))
                
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
    fixed_body = _format_cli_markdown(body_text)
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
    
    query_hash = hashlib.sha256(report.query.encode()).hexdigest()[:16]
    dash_table.add_row("QUERY HASH", query_hash)
    dash_table.add_row("ENTITIES", ", ".join(report.tickers) or "N/A")
    dash_table.add_row("TIMESTAMP", report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"))
    dash_table.add_row("VERSION", f"v{report.version}")
    
    status_style = "bold green" if report.is_valid else "bold red"
    dash_table.add_row("VALIDATION", Text("PASSED" if report.is_valid else "FAILED", style=status_style))
    
    if report.confidence_score >= 0.8:
        conf_style = "bold green"
    elif report.confidence_score >= 0.5:
        conf_style = "bold yellow"
    else:
        conf_style = "bold red"
    dash_table.add_row(
        "CONFIDENCE",
        Text(f"{report.confidence_score:.0%} ({report.confidence_score:.2f})", style=conf_style)
    )

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
    fixed_synthesis = _format_cli_markdown(report.synthesis_text)
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
        total = len(report.audit_trail)
        shown = report.audit_trail[-5:]
        for task in shown:
            desc = (task.description[:40] + "...") if len(task.description) > 40 else task.description
            audit_table.add_row(desc, task.tool, task.status)
        if total > 5:
            audit_table.add_row(
                f"[dim]... and {total - 5} more tasks (see PDF export for full trail)[/dim]",
                "", ""
            )
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
