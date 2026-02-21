from ..core.state import Task, Jasperstate
from ..tools.financials import FinancialDataRouter, FinancialDataError
from ..observability.logger import SessionLogger

# Tool name aliases — all normalised lower-case keys
_INCOME_TOOLS = {"income_statement", "financial_statement"}
_BALANCE_TOOLS = {"balance_sheet"}


# --- Executor ---
# Executes research tasks using available tools and data providers
class Executor:
    def __init__(self, financial_router: FinancialDataRouter, logger: SessionLogger | None = None):
        self.financial_router = financial_router
        self.logger = logger or SessionLogger()

    def _validate_financial_data(self, data):
        """Ensure data structure is valid before storing."""
        if isinstance(data, list):
            for report in data:
                if not isinstance(report, dict):
                    raise ValueError(f"Report is not a dict: {type(report)}")
                if "fiscalDateEnding" not in report:
                    raise ValueError("Report missing fiscalDateEnding")
        elif isinstance(data, dict):
            if not data:
                raise ValueError("Empty financial report dict")
        else:
            raise ValueError(f"Unexpected data type: {type(data)}")
        return True

    async def _execute_with_retries(
        self, state: Jasperstate, task: Task, fetch_coro_factory
    ) -> None:
        """Run a fetch coroutine with retry logic, updating task state."""
        attempts = 0
        while attempts <= state.max_retries:
            try:
                result = await fetch_coro_factory()

                if not result or (isinstance(result, list) and len(result) == 0):
                    raise FinancialDataError("Empty response from provider")

                try:
                    self._validate_financial_data(result)
                except ValueError as ve:
                    raise FinancialDataError(
                        f"Invalid financial data structure: {ve}"
                    ) from ve

                state.task_results[task.id] = result
                task.status = "completed"
                self.logger.log("TASK_EXECUTED", {"task_id": task.id, "status": task.status})
                return

            except FinancialDataError as fd_err:
                attempts += 1
                self.logger.log(
                    "TASK_RETRY",
                    {"task_id": task.id, "attempt": attempts, "error": str(fd_err)},
                )
                if attempts > state.max_retries:
                    task.status = "failed"
                    task.error = str(fd_err)
                    self.logger.log(
                        "TASK_FAILED", {"task_id": task.id, "error": str(fd_err)}
                    )
                    return

            except (KeyError, TypeError, ValueError) as e:
                task.status = "failed"
                task.error = f"Invalid data structure: {e}"
                self.logger.log("TASK_FAILED", {"task_id": task.id, "error": str(e)})
                return

    async def execute_task(self, state: Jasperstate, task: Task) -> None:
        task.status = "in_progress"

        try:
            tool = (task.tool_name or "").lower().strip()

            # Resolve ticker from tool_args
            ticker = None
            if task.tool_args:
                ticker = task.tool_args.get("ticker") or task.tool_args.get("symbol")

            if not ticker:
                raise ValueError(
                    f"No ticker found for task '{task.description}'. "
                    "The planning step must set tool_args.ticker."
                )

            if tool in _INCOME_TOOLS:
                await self._execute_with_retries(
                    state, task,
                    lambda: self.financial_router.fetch_income_statement(ticker)
                )

            elif tool in _BALANCE_TOOLS:
                await self._execute_with_retries(
                    state, task,
                    lambda: self.financial_router.fetch_balance_sheet(ticker)
                )

            else:
                raise ValueError(
                    f"Unknown tool '{tool}' for task '{task.description}'. "
                    f"Supported tools: income_statement, balance_sheet, financial_statement."
                )

        except Exception as e:
            # Only catch here if not already handled inside _execute_with_retries
            if task.status not in ("completed", "failed"):
                task.status = "failed"
                task.error = str(e)
                self.logger.log("TASK_FAILED", {"task_id": task.id, "error": str(e)})
