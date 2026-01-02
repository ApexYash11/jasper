import typer
import asyncio
from rich.console import Console
from rich.panel import Panel

from ..core.controller import JasperController
from ..agent.planner import Planner
from ..agent.executor import Executor
from ..agent.validator import validator
from ..agent.synthesizer import Synthesizer
from ..tools.financials import FinancialDataRouter
from ..tools.providers.alpha_vantage import AlphaVantageClient
from ..core.llm import get_llm
import os


console = Console()


def main(query: str = typer.Argument(..., help="The financial research question")):
    """Jasper Financial Research Agent"""
    async def run():
        # Initialize single SessionLogger and LLM (deterministic)
        from ..observability.logger import SessionLogger

        logger = SessionLogger()
        llm = get_llm(temperature=0)
        av_client = AlphaVantageClient(api_key=os.getenv("ALPHA_VANTAGE_API_KEY", "demo"))
        router = FinancialDataRouter(providers=[av_client])

        controller = JasperController(
            Planner(llm, logger=logger),
            Executor(router, logger=logger),
            validator(logger=logger),
            Synthesizer(llm, logger=logger),
            logger=logger,
        )

        console.print(Panel(f"Researching: {query}", title="Jasper"))
        state = await controller.run(query)

        # Show Execution Log
        if state.plan:
            from rich.table import Table
            table = Table(title="Execution Log")
            table.add_column("Task", style="cyan")
            table.add_column("Status", style="green")
            for task in state.plan:
                status_style = "green" if task.status == "completed" else "red" if task.status == "failed" else "yellow"
                table.add_row(task.description, f"[{status_style}]{task.status}[/{status_style}]")
            console.print(table)

        if state.status == "Failed":
            console.print("\n[bold red]Research failed[/bold red]")
            
            # Show structured validation failures
            if state.validation and state.validation.issues:
                console.print("[yellow]Validation Issues:[/yellow]")
                for issue in state.validation.issues:
                    console.print(f"  - {issue}")
            
            # Show workflow-level errors
            if state.error:
                console.print(f"[red]Error:[/red] {state.error}")
        else:
            # Show Confidence Breakdown
            if state.validation and state.validation.breakdown:
                b = state.validation.breakdown
                console.print(f"\n[bold]Confidence Breakdown:[/bold]")
                console.print(f"  - Data Coverage: {b.data_coverage:.2f}")
                console.print(f"  - Data Quality: {b.data_quality:.2f}")
                console.print(f"  - Inference Strength: {b.inference_strength:.2f}")
                console.print(f"  - [bold]Overall Confidence: {b.overall:.2f}[/bold]\n")

            answer = state.final_answer or "No answer generated."
            console.print(Panel(answer, title="Validated Answer"))

    asyncio.run(run())


if __name__ == "__main__":
    typer.run(main)
