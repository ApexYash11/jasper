from ..core.state import Task, Jasperstate
from ..tools.financials import FinancialDataRouter, FinancialDataError
from ..observability.logger import SessionLogger


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
                # Check for required fields (example)
                if "fiscalDateEnding" not in report:
                    raise ValueError("Report missing fiscalDateEnding")
        elif isinstance(data, dict):
            if not data:
                raise ValueError("Empty financial report dict")
        else:
            raise ValueError(f"Unexpected data type: {type(data)}")
        
        return True

    async def execute_task(self, state: Jasperstate, task: Task) -> None:
        task.status = "in_progress"

        try:
            # Rely on explicit tool_name
            tool = (task.tool_name or "").lower()

            if tool == "income_statement":
                # Extract ticker from tool_args if available
                ticker = None
                if task.tool_args:
                    ticker = task.tool_args.get("ticker")
                
                if not ticker:
                    # Fallback or error
                    raise ValueError(
                        f"No ticker found for task: {task.description}. "
                        f"The planning step must extract a company ticker (e.g., AAPL, MSFT)."
                    )

                # Attempt with retries based on state.max_retries
                attempts = 0
                while attempts <= state.max_retries:
                    try:
                        result = await self.financial_router.fetch_income_statement(ticker)
                        
                        # Validate the result before processing
                        if not result or (isinstance(result, list) and len(result) == 0):
                            raise FinancialDataError(f"Empty response from provider for {ticker}")
                        
                        # Add validation before storing
                        try:
                            self._validate_financial_data(result)
                        except ValueError as ve:
                            raise FinancialDataError(f"Invalid financial data structure: {str(ve)}") from ve

                        state.task_results[task.id] = result
                        task.status = "completed"
                        self.logger.log("TASK_EXECUTED", {"task_id": task.id, "status": task.status})
                        break
                    except FinancialDataError as fd_err:
                        # Retryable error; log and attempt retry
                        attempts += 1
                        self.logger.log("TASK_RETRY", {"task_id": task.id, "attempt": attempts, "error": str(fd_err)})
                        if attempts > state.max_retries:
                            task.status = "failed"
                            task.error = str(fd_err)
                            self.logger.log("TASK_FAILED", {"task_id": task.id, "error": str(fd_err)})
                            break
                    except (KeyError, TypeError, ValueError) as e:
                        # Non-retryable errors; fail immediately
                        task.status = "failed"
                        task.error = f"Invalid data structure: {str(e)}"
                        self.logger.log("TASK_FAILED", {"task_id": task.id, "error": str(e)})
                        break
            else:
                raise ValueError(f"Unknown task description: {task.description}")
          
        except (FinancialDataError, Exception) as e:
            task.status = "failed"
            task.error = str(e)
            self.logger.log("TASK_FAILED", {"task_id": task.id, "error": str(e)})
