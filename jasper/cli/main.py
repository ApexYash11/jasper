import typer
import asyncio
import os
import time
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.prompt import Prompt
from pathlib import Path

# Import core components
from ..core.controller import JasperController
from ..agent.planner import Planner
from ..agent.executor import Executor
from ..agent.validator import validator
from ..agent.synthesizer import Synthesizer
from ..tools.financials import FinancialDataRouter
from ..tools.providers.alpha_vantage import AlphaVantageClient
from ..tools.providers.yfinance import YFinanceClient
from ..core.llm import get_llm_singleton
from ..observability.logger import SessionLogger
from ..core.state import Jasperstate, FinalReport
from ..export.pdf import export_report_to_pdf, export_report_html

# Import UI components
from .interface import (
    render_banner, render_final_report, render_forensic_report,
    build_persistent_board, update_phase_node, append_task_to_node, update_synthesis_status
)
from ..core.config import THEME

console = Console()
app = typer.Typer(
    help="Institutional Financial research agent.",
    no_args_is_help=False
)

# Session cache for last report (for export)
_last_report: Optional[FinalReport] = None

# Cross-process report persistence
_CACHE_DIR = Path.home() / ".jasper"
_LAST_REPORT_PATH = _CACHE_DIR / "last_report.json"


def _save_report_to_disk(report: FinalReport) -> None:
    """Persist the last report to disk so `jasper export` works across process boundaries."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _LAST_REPORT_PATH.write_text(report.model_dump_json(), encoding="utf-8")
    except Exception:
        pass  # Non-critical — in-memory fallback still works within the session


def _load_report_from_disk() -> Optional[FinalReport]:
    """Load the last report from the disk cache (cross-process)."""
    try:
        if _LAST_REPORT_PATH.exists():
            return FinalReport.model_validate_json(
                _LAST_REPORT_PATH.read_text(encoding="utf-8")
            )
    except Exception:
        pass
    return None

@app.callback()
def main_callback(ctx: typer.Context):
    """
    Callback to show banner and handle default behavior.
    """
    if ctx.invoked_subcommand is None:
        console.clear()
        console.print(render_banner())
        console.print("\n[bold]Jasper Financial Intelligence Engine[/bold]")
        console.print("Deterministic research instrument for institutional analysts.\n")
        console.print("[dim]Usage: python -m jasper [COMMAND] [ARGS]...[/dim]\n")
        console.print("Available Commands:")
        console.print(f"  [{THEME['Accent']}]ask[/{THEME['Accent']}]         Execute a financial query directly.")
        console.print(f"  [{THEME['Accent']}]interactive[/{THEME['Accent']}] Starting the interactive research session.")
        console.print(f"  [{THEME['Accent']}]doctor[/{THEME['Accent']}]      Run system diagnostics.")
        console.print(f"  [{THEME['Accent']}]version[/{THEME['Accent']}]     Display system version information.\n")
        console.print(f"Run '[{THEME['Accent']}]python -m jasper ask --help[/{THEME['Accent']}]' for more information on a command.")

class RichLogger(SessionLogger):
    """
    Logger that manages persistent mission board with 3 phases: PLANNING → EXECUTION → SYNTHESIS
    Board is built ONCE and never rebuilt; nodes are appended to in-place.
    Uses debounced updates to avoid rendering artifacts from excessive Live widget refreshes.
    """
    def __init__(self, board_context):
        super().__init__()
        # Unpack the persistent board context
        self.live = board_context["live"]
        self.board_panel = board_context["board_panel"]
        self.planning_node = board_context["planning_node"]
        self.execution_node = board_context["execution_node"]
        self.synthesis_node = board_context["synthesis_node"]
        
        # Track task data for reference
        self.planning_tasks = {}  # {task_desc: task_obj}
        self.execution_tasks = {}
        self.synthesis_buffer = ""
        self._last_stream_update_chars = 0
        self._last_preview_text = ""
        self._task_started_at = {}

        # Keep streaming UI concise: never show full generated output in-flight
        self._preview_char_limit = 160
        self._preview_update_every_chars = 120
        
        # Debouncing: track last update time to avoid excessive Live refreshes
        self._last_update_time = 0
        self._min_update_interval = 0.05  # 50ms minimum between Live updates

    def _should_update_live(self) -> bool:
        """Check if enough time has passed since last Live update."""
        elapsed = time.perf_counter() - self._last_update_time
        if elapsed >= self._min_update_interval:
            self._last_update_time = time.perf_counter()
            return True
        return False

    def log(self, event_type: str, payload: dict):
        """Log events and update persistent board."""
        
        if event_type == "PLANNER_STARTED":
            status_line = "🔍 Analyzing query and requirements..."
            update_phase_node(self.planning_node, status_text=status_line)
            if self._should_update_live():
                self.live.update(self.board_panel)

        elif event_type == "PLAN_CREATED":
            # Initialize planning tasks
            plan = payload.get("plan", [])
            count = len(plan)
            status_line = f"📋 Decomposing query into {count} sub-tasks..."
            
            # Store task descriptions
            for task in plan:
                desc = task.get("description", "Unknown Task")
                self.planning_tasks[desc] = {"status": "pending", "detail": ""}
            
            # Update node with status + tasks
            update_phase_node(self.planning_node, status_text=status_line, tasks=[
                {
                    "description": desc,
                    "status": "pending",
                    "detail": ""
                }
                for desc in self.planning_tasks.keys()
            ])
            if self._should_update_live():
                self.live.update(self.board_panel)

        elif event_type == "TASK_STARTED":
            desc = payload.get("description")
            if desc:
                self._task_started_at[desc] = time.perf_counter()
            
            # Add to execution node (planning section stays as is)
            if desc not in self.execution_tasks:
                append_task_to_node(self.execution_node, f"► {desc}", status="running")
                self.execution_tasks[desc] = {"status": "running", "detail": ""}
            
            update_synthesis_status(self.execution_node, "⚙️  Fetching live market data...")
            if self._should_update_live():
                self.live.update(self.board_panel)

        elif event_type == "TASK_COMPLETED":
            desc = payload.get("description")
            status = payload.get("status", "pending")
            
            if desc in self.execution_tasks:
                self.execution_tasks[desc]["status"] = status

            duration_text = ""
            if desc in self._task_started_at:
                elapsed = max(0.0, time.perf_counter() - self._task_started_at.pop(desc))
                duration_text = f" ({elapsed:.1f}s)"

            if desc:
                if status == "completed":
                    append_task_to_node(self.execution_node, f"✔ {desc}{duration_text}", status="success")
                    update_synthesis_status(self.execution_node, f"✅ Completed: {desc[:60]}{duration_text}")
                else:
                    append_task_to_node(self.execution_node, f"✖ {desc}{duration_text}", status="failed")
                    update_synthesis_status(self.execution_node, f"⚠️ Failed: {desc[:60]}{duration_text}")
            
            # Force update for task completion (always show immediately)
            self.live.update(self.board_panel)
            self._last_update_time = time.perf_counter()

        elif event_type == "ENTITY_EXTRACTION_STARTED":
            update_synthesis_status(self.planning_node, "🔍 Identifying entities & intent...")
            if self._should_update_live():
                self.live.update(self.board_panel)

        elif event_type == "MODE_INFERRED":
            mode = payload.get("mode", "").upper()
            update_synthesis_status(self.planning_node, f"📋 Mode: {mode} — building task plan...")
            if self._should_update_live():
                self.live.update(self.board_panel)

        elif event_type == "VALIDATION_STARTED":
            update_synthesis_status(self.synthesis_node, "✓ Verifying data integrity...")
            if self._should_update_live():
                self.live.update(self.board_panel)

        elif event_type == "SYNTHESIS_STARTED":
            update_synthesis_status(self.synthesis_node, "✍️  Compiling executive report...")
            if self._should_update_live():
                self.live.update(self.board_panel)

        elif event_type == "REFLECTION_STARTED":
            update_synthesis_status(self.execution_node, "🔄 Checking for recoverable failures...")
            if self._should_update_live():
                self.live.update(self.board_panel)

        elif event_type == "REFLECTOR_RETRYING":
            desc = payload.get("description", "task")[:50]
            attempt = payload.get("attempt", 1)
            update_synthesis_status(self.execution_node, f"🔁 Retry {attempt}: {desc}...")
            if self._should_update_live():
                self.live.update(self.board_panel)

        elif event_type == "REFLECTOR_COMPLETED":
            recovered = payload.get("recovered", 0)
            still_failed = payload.get("still_failed", 0)
            if recovered > 0:
                status = f"✅ Recovered {recovered} task(s)"
            elif still_failed > 0:
                status = f"⚠️ {still_failed} task(s) unrecoverable — proceeding with partial data"
            else:
                status = "✅ All tasks nominal"
            update_synthesis_status(self.execution_node, status)
            if self._should_update_live():
                self.live.update(self.board_panel)

        elif event_type == "VALIDATION_COMPLETED":
            conf = payload.get("confidence", 0)
            is_valid = payload.get("is_valid", False)
            if is_valid:
                status = f"✅ Confidence: {conf:.0%} — Starting synthesis..."
            else:
                status = f"❌ Validation failed (confidence: {conf:.0%})"
            update_synthesis_status(self.synthesis_node, status)
            # Force update for validation completion (always show immediately)
            self.live.update(self.board_panel)
            self._last_update_time = time.perf_counter()

    def on_synthesis_token(self, token: str) -> None:
        """
        Called by synthesizer for each streamed token.
        Streams a SHORT preview only (never full in-flight output).
        Updates at sentence boundaries or periodic character intervals.
        Uses debouncing to avoid overwhelming the Live widget.
        """
        self.synthesis_buffer += token
        
        # Only update UI at safe boundary conditions:
        # 1. After a sentence ending (., !, ?)
        # 2. Every N accumulated characters (to show progress)
        should_update = False
        
        if token.rstrip().endswith((".", "!", "?")):
            should_update = True
        elif len(self.synthesis_buffer) - self._last_stream_update_chars >= self._preview_update_every_chars:
            should_update = True
        
        if should_update and self._should_update_live():
            # Show short sanitized preview - avoid echoing full model output
            normalized = " ".join(self.synthesis_buffer.split()).strip()
            if not normalized:
                return

            if len(normalized) > self._preview_char_limit:
                preview = "..." + normalized[-self._preview_char_limit:]
            else:
                preview = normalized
            
            # Filter out low-value content (disclaimers, methodology)
            if not self._is_low_value_content(preview) and preview != self._last_preview_text:
                update_synthesis_status(self.synthesis_node, f"✍️  {preview}▌")
                self.live.update(self.board_panel)
                self._last_preview_text = preview

            self._last_stream_update_chars = len(self.synthesis_buffer)
    
    def _is_low_value_content(self, text: str) -> bool:
        """
        Check if content is low-value disclaimer/metadata that shouldn't be shown.
        Prioritizes showing key analytical content sections.
        """
        text_lower = text.lower()
        
        # High-value sections that should ALWAYS be shown
        key_sections = [
            "executive summary",
            "key findings",
            "findings",
            "recommendations",
            "business model",
            "financial metrics",
            "financial evidence",
            "valuation",
            "growth drivers",
            "risks",
            "competitive advantages",
            "segments",
            "profitability",
        ]
        
        # Check if this is part of a key section
        for section in key_sections:
            if section in text_lower:
                return False  # This is valuable content
        
        # Low-value phrases that indicate metadata/disclaimers
        low_value_phrases = [
            "not investment advice",
            "past performance",
            "disclaimer",
            "methodology",
            "data source",
            "confidential",
            "analyst output",
            "is intended",
            "should not",
            "seek professional advice",
            "for informational purposes",
            "not a substitute",
            "verify independently",
        ]
        
        return any(phrase in text_lower for phrase in low_value_phrases)

async def execute_research(query: str, console: Console) -> Jasperstate:
    # Build the persistent board ONCE (never rebuilt)
    board_panel, planning_node, execution_node, synthesis_node = build_persistent_board()
    
    # Initialize planning node with startup message
    update_phase_node(planning_node, status_text="🚀 Initializing research engine...")
    
    with Live(board_panel, refresh_per_second=4, console=console) as live:
        # Initialize Logger with persistent board context
        board_context = {
            "live": live,
            "board_panel": board_panel,
            "planning_node": planning_node,
            "execution_node": execution_node,
            "synthesis_node": synthesis_node
        }
        logger = RichLogger(board_context)
        
        # Reuse module-level LLM singleton — avoids rebuilding the connection pool
        llm = get_llm_singleton(temperature=0)
        av_client = AlphaVantageClient(api_key=os.getenv("ALPHA_VANTAGE_API_KEY", "demo"))
        yfinance_client = YFinanceClient()
        router = FinancialDataRouter(providers=[av_client, yfinance_client])

        controller = JasperController(
            Planner(llm, logger=logger),
            Executor(router, logger=logger),
            validator(logger=logger),
            Synthesizer(llm, logger=logger),
            logger=logger,
        )

        # Run Controller
        state = await controller.run(query)
        
    # After Live block, show results
    await asyncio.sleep(0.2) # Short pause to give report "weight"
    console.print("\n")
    
    if state.status == "Failed":
        console.print(f"[bold {THEME['Error']}]Research Failed[/bold {THEME['Error']}]")
        if state.error:
            error_source = state.error_source or "unknown"
            
            # LLM Service Errors
            if error_source == "llm_service":
                console.print(f"[yellow]⚠ LLM Service Error:[/yellow] {state.error}")
                console.print("[dim]The AI model (OpenRouter) is temporarily unavailable or rate-limited.[/dim]")
                console.print("[dim]Suggestion: Wait a moment and try again, or check your OpenRouter quota.[/dim]")
            elif error_source == "llm_auth":
                console.print(f"[yellow]⚠ LLM Authentication Error:[/yellow] {state.error}")
                console.print("[dim]Your OPENROUTER_API_KEY may be invalid or expired.[/dim]")
                console.print("[dim]Suggestion: Check your .env file and ensure the key is correct.[/dim]")
            elif error_source == "llm_timeout":
                console.print(f"[yellow]⚠ LLM Timeout:[/yellow] {state.error}")
                console.print("[dim]The request to the AI model took too long.[/dim]")
                console.print("[dim]Suggestion: Try again, or try a simpler query.[/dim]")
            elif error_source in ("llm_unknown", "llm"):
                console.print(f"[yellow]⚠ Answer Synthesis Error:[/yellow] {state.error}")
                console.print("[dim]Failed to generate the final answer. Data was fetched but answer generation failed.[/dim]")
                console.print("[dim]Suggestion: Try again or simplify your query.[/dim]")
            # Data Provider Errors
            elif error_source == "data_provider":
                console.print(f"[yellow]⚠ Data Provider Error:[/yellow] {state.error}")
                console.print("[dim]Could not fetch financial data from available providers.[/dim]")
                console.print("[dim]Suggestion: Check the ticker symbol (e.g., AAPL, RELIANCE.NS, INFY.NS) or try a different company.[/dim]")
            # Query Issues
            elif error_source == "query":
                console.print(f"[yellow]⚠ Query Error:[/yellow] {state.error}")
                console.print("[dim]The query could not be understood or mapped to a tool.[/dim]")
                console.print("[dim]Suggestion: Try rephrasing with a company name or ticker symbol.[/dim]")
            # Generic
            else:
                console.print(f"Error: {state.error}")
                
        if state.validation and state.validation.issues:
            console.print("[yellow]Validation Issues:[/yellow]")
            for issue in state.validation.issues:
                console.print(f"  - {issue}")
    else:
        # Show Final Report with Confidence Breakdown and Answer
        answer = state.final_answer or "No answer generated."
        
        # Extract tickers and sources for the report header
        tickers = []
        sources = set()
        for task in state.plan:
            if task.tool_args:
                ticker = task.tool_args.get("ticker") or task.tool_args.get("symbol")
                if ticker:
                    tickers.append(ticker.upper())
            if task.tool_name:
                sources.add(task.tool_name.replace("_", " ").title())
        
        # Deduplicate tickers while preserving order
        unique_tickers = []
        for t in tickers:
            if t not in unique_tickers:
                unique_tickers.append(t)
        
        # Fallbacks
        if not unique_tickers:
            unique_tickers = ["Unknown Entity"]
        if not sources:
            sources = {"SEC EDGAR"} # Default fallback source
        
        # v0.2.0: Forensic Rendering if report exists
        if state.report:
            console.print(render_forensic_report(state.report))
            
            # Manual export via /export command (auto-export disabled)
            console.print(f"[dim]Tip: Use [{THEME['Accent']}]/export[/{THEME['Accent']}] to save PDF[/dim]")
        else:
            # Fallback to legacy memo
            console.print(render_final_report(answer, unique_tickers, list(sources)))
        
        console.print("\n")
    
    return state
@app.command(name="ask")
def ask_command(query: str = typer.Argument(..., help="Financial research question (e.g., 'What is Apple revenue?')")):
    """Execute financial research on a query.
    
    Example:
        jasper ask "What is Apple's current revenue?"
    """
    # TYPE GUARD: Ensure query is a string (prevent Typer ArgumentInfo leakage)
    if not isinstance(query, str) or not query.strip():
        console.print("[bold red]Error:[/bold red] Query must be a non-empty string")
        raise typer.Exit(code=1)
    
    # Preflight configuration checks
    try:
        from ..core.config import get_llm_api_key, get_financial_api_key
        get_llm_api_key()
        get_financial_api_key()
    except ValueError as e:
        console.print(f"[bold {THEME['Error']}]Setup Error:[/bold {THEME['Error']}] {str(e)}")
        raise typer.Exit(code=1)
    
    # Execute research
    console.clear()
    console.print(render_banner())
    console.print(f"\n[{THEME['Accent']}]Researching:[/{THEME['Accent']}] {query}\n")

    # Warn visibly when no real AV key is configured
    if not os.getenv("ALPHA_VANTAGE_API_KEY"):
        console.print(
            f"[bold {THEME['Warning']}]⚠  DEMO MODE:[/bold {THEME['Warning']}]"
            f"[{THEME['Warning']}] No ALPHA_VANTAGE_API_KEY set. "
            f"Alpha Vantage will return IBM data for ALL tickers. "
            f"Falling back to yfinance where possible.[/{THEME['Warning']}]\n"
        )

    state = asyncio.run(execute_research(query, console))
    
    # Cache the report for export command
    global _last_report
    _last_report = state.report
    if state.report:
        _save_report_to_disk(state.report)

    return state


# =====================================================================
# COMMAND 1: ask <query>  —  Execute financial research
# =====================================================================


# =====================================================================
# COMMAND 2: version  —  Show version only (no research)
# =====================================================================
@app.command(name="version")
def version_command():
    """Show Jasper version."""
    try:
        from importlib.metadata import version as pkg_version
        version = pkg_version("jasper-finance")
    except Exception:
        from .. import __version__
        version = __version__

    console.print(f"[bold cyan]Jasper[/bold cyan] version [bold green]{version}[/bold green]")


# =====================================================================
# COMMAND 3: doctor  —  Run diagnostics only (no research)
# =====================================================================
@app.command(name="doctor")
def doctor_command():
    """Run configuration and setup diagnostics."""
    console.print(render_banner())
    console.print("\n[bold cyan]Running Diagnostics...[/bold cyan]\n")
    
    issues = []
    
    # Check 1: OPENROUTER_API_KEY
    llm_key = os.getenv("OPENROUTER_API_KEY")
    if llm_key:
        console.print("[green]✓[/green] OPENROUTER_API_KEY is set")
    else:
        console.print("[yellow]✗[/yellow] OPENROUTER_API_KEY is not set")
        issues.append("OPENROUTER_API_KEY required for LLM operations")
    
    # Check 2: ALPHA_VANTAGE_API_KEY (optional, but warn if missing)
    av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if av_key:
        console.print("[green]✓[/green] ALPHA_VANTAGE_API_KEY is set")
    else:
        console.print("[dim]ℹ[/dim] ALPHA_VANTAGE_API_KEY is not set (demo mode will be used)")
    
    # Check 3: Python version
    import sys
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info >= (3, 9):
        console.print(f"[green]✓[/green] Python {py_version} (requirement: ≥3.9)")
    else:
        console.print(f"[red]✗[/red] Python {py_version} is too old (requirement: ≥3.9)")
        issues.append(f"Python 3.9+ required (you have {py_version})")
    
    # Check 4: Try importing core modules
    try:
        from ..core.llm import get_llm
        console.print("[green]✓[/green] Core modules import successfully")
    except ImportError as e:
        console.print(f"[red]✗[/red] Core module import failed: {e}")
        issues.append("Core modules cannot be imported")
    
    # Check 5: Try initializing LLM (only if API key exists)
    if llm_key:
        try:
            from ..core.llm import get_llm
            get_llm(temperature=0)
            console.print("[green]✓[/green] LLM initialization works")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] LLM initialization failed: {e}")
            issues.append("LLM initialization issue (check your OPENROUTER_API_KEY)")
    
    # Summary
    console.print("\n")
    if not issues:
        console.print("[bold green]All checks passed! Jasper is ready to use.[/bold green]")
        raise typer.Exit(code=0)
    else:
        console.print(f"[bold yellow]Found {len(issues)} issue(s):[/bold yellow]")
        for issue in issues:
            console.print(f"  [yellow]•[/yellow] {issue}")
        raise typer.Exit(code=1)


# =====================================================================
# INTERACTIVE MODE: ask with no args → REPL
# =====================================================================
@app.command(name="interactive")
def interactive_command():
    """Run Jasper in interactive mode (REPL).
    
    Type financial questions, get answers. Type 'exit' to quit.
    Each query is processed independently with full intent classification.
    """
    # Preflight checks
    try:
        from ..core.config import get_llm_api_key, get_financial_api_key
        get_llm_api_key()
        get_financial_api_key()
    except ValueError as e:
        console.print(f"[bold {THEME['Error']}]Setup Error:[/bold {THEME['Error']}] {str(e)}")
        raise typer.Exit(code=1)
    
    # REPL Loop
    console.clear()
    console.print(render_banner())
    console.print(f"\n[{THEME['Primary Text']}]Interactive Mode. Type 'exit' to quit.[/{THEME['Primary Text']}]")
    console.print(f"[{THEME['Primary Text']}]Commands: [/{THEME['Primary Text']}][{THEME['Accent']}]/export[/{THEME['Accent']}] (Save PDF), [{THEME['Accent']}]/html[/{THEME['Accent']}] (Save HTML)\n")
    
    global _last_report
    history = []
    
    while True:
        try:
            user_input = Prompt.ask(f"[{THEME['Accent']}]?[/{THEME['Accent']}] Enter Financial Query").strip()
            
            if user_input.lower() in ("exit", "quit", "/bye"):
                console.print("[bold]Goodbye![/bold]")
                break
            
            if not user_input:
                continue

            # Handle Export Commands
            if user_input.lower().startswith("/export"):
                if _last_report is None:
                    console.print("[yellow]⚠ No report to export. Run a research query first.[/yellow]")
                    continue
                
                parts = user_input.split()
                if len(parts) > 1:
                    out_file = parts[1]
                else:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    out_file = f"jasper_report_{ts}.pdf"
                try:
                    pdf_path = export_report_to_pdf(_last_report, out_file, validate=True)
                    console.print(f"[bold green]✅ PDF exported:[/bold green] {pdf_path}")
                except Exception as e:
                    console.print(f"[red]Error exporting PDF: {e}[/red]")
                continue

            if user_input.lower().startswith("/html"):
                if _last_report is None:
                    console.print("[yellow]⚠ No report to export. Run a research query first.[/yellow]")
                    continue
                
                parts = user_input.split()
                if len(parts) > 1:
                    out_file = parts[1]
                else:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    out_file = f"jasper_report_{ts}.html"
                try:
                    html_path = export_report_html(_last_report, out_file)
                    console.print(f"[bold green]✅ HTML exported:[/bold green] {html_path}")
                except Exception as e:
                    console.print(f"[red]Error exporting HTML: {e}[/red]")
                continue

            # Execute Research — prepend recent history for session memory (#19)
            effective_query = user_input
            if history:
                context_lines = []
                for prev_q, prev_a in history[-3:]:
                    # Truncate prior answers to avoid flooding the prompt
                    snippet = (prev_a or "")[:300].replace("\n", " ")
                    ellipsis = "..." if len(prev_a or "") > 300 else ""
                    context_lines.append(
                        f"Prior Q: {prev_q}\nPrior A (summary): {snippet}{ellipsis}"
                    )
                context_prefix = (
                    "PRIOR SESSION CONTEXT (for follow-up awareness only):\n"
                    + "\n".join(context_lines)
                    + "\n\nCURRENT QUERY: "
                )
                effective_query = context_prefix + user_input

            console.print(f"\n[{THEME['Accent']}]Researching:[/{THEME['Accent']}] {user_input}\n")
            
            state = asyncio.run(execute_research(effective_query, console))
            
            # Update cache
            if state.report:
                _last_report = state.report
                _save_report_to_disk(state.report)
            
            if state.status == "Completed" and state.validation and state.validation.is_valid:
                history.append((user_input, state.final_answer))
            
            console.print("\n")
            
        except KeyboardInterrupt:
            console.print("\n[bold]Goodbye![/bold]")
            break


# =====================================================================
# COMMAND 5: export  —  Export research report to PDF
# =====================================================================
@app.command(name="export")
def export_command(format: str = "pdf", out: str = ""):
    """Export the last research report to PDF or HTML.
    
    Examples:
        python -m jasper export
        python -m jasper export pdf apple.pdf
        python -m jasper export html apple.html
    
    Arguments:
        format (str): Export format: pdf or html (default: pdf)
        out (str): Output file path (default: timestamped filename)
    """
    global _last_report

    # Try loading from disk if not in memory (cross-process usage)
    if _last_report is None:
        _last_report = _load_report_from_disk()

    if _last_report is None:
        console.print(f"[bold {THEME['Error']}]Error:[/bold {THEME['Error']}] No report to export.")
        console.print("[dim]Run a research query first:[/dim]")
        console.print(f"  [{THEME['Accent']}]python -m jasper ask 'What is Apple revenue?'[/{THEME['Accent']}]")
        raise typer.Exit(code=1)
    
    format = format.lower().strip()

    # Auto-generate a timestamped filename if none provided
    if not out:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = f"jasper_report_{ts}.{format}"
    
    # Export based on format
    try:
        if format == "pdf":
            pdf_path = export_report_to_pdf(_last_report, out, validate=True)
            console.print(f"[bold green]✅ PDF exported:[/bold green] {pdf_path}")
            console.print(f"   Size: {Path(pdf_path).stat().st_size:,} bytes")
            console.print(f"   Confidence: {_last_report.confidence_score:.1%}")
            console.print(f"   Valid: {_last_report.is_valid}")
            
        elif format == "html":
            html_path = export_report_html(_last_report, out)
            console.print(f"[bold green]✅ HTML exported:[/bold green] {html_path}")
            console.print("[dim]Open in browser to preview layout[/dim]")
            
        else:
            console.print(f"[bold {THEME['Error']}]Error:[/bold {THEME['Error']}] Unsupported format '{format}'")
            console.print("[dim]Supported formats: 'pdf', 'html'[/dim]")
            raise typer.Exit(code=1)
    
    except ValueError as e:
        console.print(f"[bold {THEME['Error']}]Export Failed:[/bold {THEME['Error']}]")
        console.print(f"[yellow]{str(e)}[/yellow]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold {THEME['Error']}]Error:[/bold {THEME['Error']}] {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
