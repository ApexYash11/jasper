from ..agent.planner import Planner
from ..agent.executor import Executor
from ..agent.validator import validator
from ..agent.synthesizer import Synthesizer
from .state import Jasperstate
from ..observability.logger import SessionLogger


# --- Jasper Controller ---
# Orchestrates the flow between Planner, Executor, Validator, and Synthesizer
class JasperController:
    def __init__(self, planner: Planner, executor: Executor, validator: validator, synthesizer: Synthesizer, logger: SessionLogger | None = None):
        self.planner = planner
        self.executor = executor
        self.validator = validator
        self.synthesizer = synthesizer
        # Use provided logger to keep session_id consistent across components
        self.logger = logger or SessionLogger()

    async def run(self, query: str) -> Jasperstate:
        """Step through the entire workflow: plan → execute → validate → synthesize."""
        state = Jasperstate(query=query)
        state.status = "Planning"
        try:
            # Planning phase
            state.plan = await self.planner.plan(query)
            self.logger.log("PLAN_CREATED", {"plan": [t.dict() for t in state.plan]})
            state.status = "Executing"

            # Execution phase
            for idx, task in enumerate(state.plan):
                state.current_task_index = idx
                self.logger.log("TASK_STARTED", {"task_id": task.id, "description": task.description})
                await self.executor.execute_task(state, task)
                self.logger.log("TASK_COMPLETED", {"task_id": task.id, "status": task.status})

            # Validation phase
            state.status = "Validating"
            try:
                state.validation = self.validator.validate(state)
            except Exception as e:
                self.logger.log("VALIDATION_ERROR", {"error": str(e)})
                state.status = "Failed"
                state.error = f"Validation error: {str(e)}"
                return state

            if not state.validation.is_valid:
                self.logger.log("VALIDATION_FAILED", {"issues": state.validation.issues})
                state.status = "Failed"
                return state

            # Synthesis phase
            state.status = "Synthesizing"
            try:
                state.final_answer = await self.synthesizer.synthesize(state)
                self.logger.log("FINAL_ANSWER", {"answer": state.final_answer})
                state.status = "Completed"
            except Exception as e:
                # Distinguish LLM errors from other failures
                error_msg = str(e)
                if "524" in error_msg or "provider returned error" in error_msg.lower():
                    state.error = f"LLM service error (code 524): Temporary rate limit. Please try again in a moment."
                    state.error_source = "llm_service"
                elif "401" in error_msg or "unauthorized" in error_msg.lower():
                    state.error = "LLM authentication failed. Check your OpenRouter API key."
                    state.error_source = "llm_auth"
                elif "timeout" in error_msg.lower():
                    state.error = "LLM request timed out. Please try again."
                    state.error_source = "llm_timeout"
                else:
                    state.error = f"Answer synthesis failed: {error_msg}"
                    state.error_source = "llm_unknown"
                self.logger.log("SYNTHESIS_ERROR", {"error": state.error, "source": state.error_source})
                state.status = "Failed"
            return state

        except Exception as e:
            # Surface any unexpected errors as structured failure
            self.logger.log("WORKFLOW_ERROR", {"error": str(e)})
            state.status = "Failed"
            # attach error for CLI visibility
            state.error = str(e)
            return state
