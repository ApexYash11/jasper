import typer
import asyncio
import os
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
app = typer.Typer()

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
        
        metrics = []
        if state.validation and state.validation.breakdown:
            b = state.validation.breakdown
            metrics = [
                {"Metric": "Data Coverage", "Value": f"{b.data_coverage:.2f}", "Source": "Validator"},
                {"Metric": "Data Quality", "Value": f"{b.data_quality:.2f}", "Source": "Validator"},
                {"Metric": "Inference Strength", "Value": f"{b.inference_strength:.2f}", "Source": "Validator"},
                {"Metric": "Overall Confidence", "Value": f"{b.overall:.2f}", "Source": "Validator"},
            ]
        
        console.print(render_final_report(answer, metrics))
        console.print("\n")
    
    return state

@app.command()
def main(query: str = typer.Argument(None, help="The financial research question")):
    """Jasper Financial Research Agent"""
    
    # Preflight checks
    try:
        from ..core.config import get_llm_api_key, get_financial_api_key
        get_llm_api_key()
        get_financial_api_key()
    except ValueError as e:
        console.print(f"[bold {THEME['Error']}]Setup Error:[/bold {THEME['Error']}] {str(e)}", style=THEME['Error'])
        raise typer.Exit(code=1)

    if query:
        # Single run
        console.clear()
        console.print(render_banner())
        console.print(f"\n[{THEME['Accent']}]Researching:[/{THEME['Accent']}] {query}\n")
        asyncio.run(execute_research(query, console))
    else:
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
