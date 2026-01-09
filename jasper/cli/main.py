import typer
import asyncio
import os
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt

# Import core components
from ..core.controller import JasperController
from ..agent.planner import Planner
from ..agent.executor import Executor
from ..agent.validator import validator
from ..agent.synthesizer import Synthesizer
from ..tools.financials import FinancialDataRouter
from ..tools.providers.alpha_vantage import AlphaVantageClient
from ..tools.providers.yfinance import YFinanceClient
from ..core.llm import get_llm
from ..observability.logger import SessionLogger
from ..core.state import Jasperstate

# Import UI components
from .interface import render_banner, render_mission_board, render_final_report
from ..core.config import THEME

console = Console()
app = typer.Typer(
    invoke_without_command=True,
    rich_markup_mode="rich",
    help="Institutional Financial research agent.",
    no_args_is_help=False
)

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
    def __init__(self, live: Live):
        super().__init__()
        self.live = live
        self.tasks = [] # List of task dicts for render_mission_board

    def log(self, event_type: str, payload: dict):
        # Override to update UI instead of printing JSON
        
        if event_type == "PLAN_CREATED":
            # Initialize tasks from plan
            self.tasks = [
                {"description": t.get("description", "Unknown Task"), "status": "pending", "detail": ""}
                for t in payload.get("plan", [])
            ]
            self.live.update(render_mission_board(self.tasks))

        elif event_type == "TASK_STARTED":
            # Update task status to running
            desc = payload.get("description")
            for t in self.tasks:
                if t["description"] == desc:
                    t["status"] = "running"
                    t["detail"] = "Executing..."
                    break
            self.live.update(render_mission_board(self.tasks))

        elif event_type == "TASK_COMPLETED":
            # Find the running task and mark completed
            status = payload.get("status")
            for t in self.tasks:
                if t["status"] == "running":
                    t["status"] = "success" if status == "completed" else "failed"
                    t["detail"] = ""
                    break
            self.live.update(render_mission_board(self.tasks))

async def execute_research(query: str, console: Console) -> Jasperstate:
    # Setup Live display with initial empty board
    with Live(render_mission_board([]), refresh_per_second=10, console=console) as live:
        
        # Initialize Logger with Live reference
        logger = RichLogger(live)
        
        # Initialize Components
        llm = get_llm(temperature=0)
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
    console.print("\n")
    
    if state.status == "Failed":
        console.print(f"[bold {THEME['Error']}]Research Failed[/bold {THEME['Error']}]")
        if state.error:
            error_source = state.error_source or "unknown"
            
            # LLM Service Errors
            if error_source == "llm_service":
                console.print(f"[yellow]⚠ LLM Service Error:[/yellow] {state.error}")
                console.print(f"[dim]The AI model (OpenRouter) is temporarily unavailable or rate-limited.[/dim]")
                console.print(f"[dim]Suggestion: Wait a moment and try again, or check your OpenRouter quota.[/dim]")
            elif error_source == "llm_auth":
                console.print(f"[yellow]⚠ LLM Authentication Error:[/yellow] {state.error}")
                console.print(f"[dim]Your OPENROUTER_API_KEY may be invalid or expired.[/dim]")
                console.print(f"[dim]Suggestion: Check your .env file and ensure the key is correct.[/dim]")
            elif error_source == "llm_timeout":
                console.print(f"[yellow]⚠ LLM Timeout:[/yellow] {state.error}")
                console.print(f"[dim]The request to the AI model took too long.[/dim]")
                console.print(f"[dim]Suggestion: Try again, or try a simpler query.[/dim]")
            elif error_source in ("llm_unknown", "llm"):
                console.print(f"[yellow]⚠ Answer Synthesis Error:[/yellow] {state.error}")
                console.print(f"[dim]Failed to generate the final answer. Data was fetched but answer generation failed.[/dim]")
                console.print(f"[dim]Suggestion: Try again or simplify your query.[/dim]")
            # Data Provider Errors
            elif error_source == "data_provider":
                console.print(f"[yellow]⚠ Data Provider Error:[/yellow] {state.error}")
                console.print(f"[dim]Could not fetch financial data from available providers.[/dim]")
                console.print(f"[dim]Suggestion: Check the ticker symbol (e.g., AAPL, RELIANCE.NS, INFY.NS) or try a different company.[/dim]")
            # Query Issues
            elif error_source == "query":
                console.print(f"[yellow]⚠ Query Error:[/yellow] {state.error}")
                console.print(f"[dim]The query could not be understood or mapped to a tool.[/dim]")
                console.print(f"[dim]Suggestion: Try rephrasing with a company name or ticker symbol.[/dim]")
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
        
        console.print(render_final_report(answer, unique_tickers, list(sources)))
        console.print("\n")
    
    return state


# =====================================================================
# COMMAND 1: ask <query>  —  Execute financial research
# =====================================================================
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
    asyncio.run(execute_research(query, console))


# =====================================================================
# COMMAND 2: version  —  Show version only (no research)
# =====================================================================
@app.command(name="version")
def version_command():
    """Show Jasper version."""
    # Read version from pyproject.toml
    try:
        import tomllib
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            version = data["project"]["version"]
    except Exception:
        # Fallback if toml parsing fails
        version = "0.2.0"
    
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
        from ..core.controller import JasperController
        from ..core.state import Jasperstate
        from ..core.llm import get_llm
        console.print("[green]✓[/green] Core modules import successfully")
    except ImportError as e:
        console.print(f"[red]✗[/red] Core module import failed: {e}")
        issues.append("Core modules cannot be imported")
    
    # Check 5: Try initializing LLM (only if API key exists)
    if llm_key:
        try:
            from ..core.llm import get_llm
            llm = get_llm(temperature=0)
            console.print("[green]✓[/green] LLM initialization works")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] LLM initialization failed: {e}")
            issues.append("LLM initialization issue (check your OPENROUTER_API_KEY)")
    
    # Summary
    console.print(f"\n")
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
    console.print(f"\n[{THEME['Primary Text']}]Interactive Mode. Type 'exit' to quit.[/{THEME['Primary Text']}]\n")
    
    history = []
    
    while True:
        try:
            user_input = Prompt.ask(f"[{THEME['Accent']}]?[/{THEME['Accent']}] Enter Financial Query")
            if user_input.lower() in ("exit", "quit", "/bye"):
                console.print("[bold]Goodbye![/bold]")
                break
            
            if not user_input.strip():
                continue

            effective_query = user_input
            if history:
                context_str = "\n".join([f"Q: {q}\nA: {a}" for q, a in history[-2:]])
                effective_query = f"PREVIOUS CONTEXT:\n{context_str}\n\nCURRENT QUERY:\n{user_input}"

            console.print(f"\n[{THEME['Accent']}]Researching:[/{THEME['Accent']}] {user_input}\n")
            
            state = asyncio.run(execute_research(effective_query, console))
            
            if state.status == "Completed" and state.validation and state.validation.is_valid:
                history.append((user_input, state.final_answer))
            
            console.print("\n")
            
        except KeyboardInterrupt:
            console.print("\n[bold]Goodbye![/bold]")
            break


if __name__ == "__main__":
    app()
