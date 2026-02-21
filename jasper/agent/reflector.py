"""
Reflector — retry/recovery node for the Jasper pipeline.

Called by the controller after the Executor finishes, before Validation.
Inspects failed tasks and either retries them (for transient errors) or
gracefully marks them as skipped so the pipeline can proceed with partial data.

Transforms Jasper from "all-or-nothing" to "best-effort with transparency".
"""

from ..core.state import Jasperstate
from ..observability.logger import SessionLogger

# Substrings in task.error that indicate a transient / retryable condition
_RETRYABLE_KEYWORDS = [
    "timeout", "timed out", "connection", "503", "502",
    "429", "rate limit", "too many requests", "temporarily unavailable",
]


def _is_retryable(error: str) -> bool:
    """Return True if the error looks like a transient network/rate-limit issue."""
    lower = error.lower()
    return any(kw in lower for kw in _RETRYABLE_KEYWORDS)


class Reflector:
    """
    Post-execution recovery agent.

    Workflow:
    1. Scan the plan for tasks in 'failed' status.
    2. For transient errors (network/rate-limit) — reset to 'pending' and
       re-execute via the provided executor.
    3. For permanent errors (invalid ticker, no data) — leave as 'failed'
       so the validator can surface them cleanly.
    4. The partial-success validator then decides whether to proceed.
    """

    def __init__(self, max_retries: int = 1, logger: SessionLogger | None = None):
        self.max_retries = max_retries
        self.logger = logger or SessionLogger()

    async def reflect(self, state: Jasperstate, executor) -> Jasperstate:
        """
        Retry failed tasks and degrade gracefully where recovery is impossible.

        Args:
            state:    Current pipeline state (mutated in-place).
            executor: The Executor instance used to re-run failed tasks.

        Returns:
            The (possibly updated) state.
        """
        failed_tasks = [t for t in state.plan if t.status == "failed"]
        if not failed_tasks:
            return state

        self.logger.log("REFLECTOR_STARTED", {
            "failed_count": len(failed_tasks),
            "total_tasks": len(state.plan),
        })

        for task in failed_tasks:
            original_error = task.error or ""
            if _is_retryable(original_error):
                self.logger.log("REFLECTOR_RETRYING", {
                    "task_id": task.id, "description": task.description,
                    "error": original_error,
                })
                task.status = "pending"
                task.error = None
                await executor.execute_task(state, task)

                log_event = (
                    "REFLECTOR_RETRY_SUCCESS" if task.status == "completed"
                    else "REFLECTOR_RETRY_FAILED"
                )
                self.logger.log(log_event, {
                    "task_id": task.id, "error": task.error,
                })
            else:
                self.logger.log("REFLECTOR_SKIPPING", {
                    "task_id": task.id, "reason": original_error,
                })

        recovered = sum(1 for t in state.plan if t.status == "completed")
        self.logger.log("REFLECTOR_COMPLETED", {
            "recovered": recovered,
            "still_failed": len(state.plan) - recovered,
        })
        return state
