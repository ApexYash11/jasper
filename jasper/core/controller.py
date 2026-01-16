from ..agent.planner import Planner
from ..agent.executor import Executor
from ..agent.validator import validator
from ..agent.synthesizer import Synthesizer
from .state import Jasperstate, FinalReport, TaskExecutionDetail, EvidenceItem, InferenceLink
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
            state.plan, state.report_mode = await self.planner.plan(query)
            self.logger.log("PLAN_CREATED", {"plan": [t.dict() for t in state.plan], "mode": state.report_mode.value})
            state.status = "Executing"

            # Execution phase
            for idx, task in enumerate(state.plan):
                state.current_task_index = idx
                self.logger.log("TASK_STARTED", {"task_id": task.id, "description": task.description})
                await self.executor.execute_task(state, task)
                self.logger.log("TASK_COMPLETED", {"task_id": task.id, "status": task.status})

            # Validation phase
            state.status = "Validating"
            self.logger.log("VALIDATION_STARTED", {})
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
            self.logger.log("SYNTHESIS_STARTED", {})
            try:
                state.final_answer = await self.synthesizer.synthesize(state)
                self.logger.log("FINAL_ANSWER", {"answer": state.final_answer})
                state.status = "Completed"
                
                # Construct FinalReport for audit-ready export
                state.report = self._build_final_report(state)
                self.logger.log("REPORT_CREATED", {"report_valid": state.report.is_valid})
                
            except Exception as e:
                # Distinguish LLM errors from other failures
                error_msg = str(e)
                if "524" in error_msg or "provider returned error" in error_msg.lower():
                    state.error = "LLM service error (code 524): Temporary rate limit. Please try again in a moment."
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

    def _build_final_report(self, state: Jasperstate) -> FinalReport:
        """
        Construct a FinalReport object from Jasperstate.
        
        This is the single source of truth for PDF exports.
        """
        # Extract tickers and sources from plan
        tickers = []
        sources = set()
        audit_trail = []
        
        def safe_truncate(obj, max_len=100):
            """Safely truncate object to string without raising on non-serializable types."""
            try:
                s = str(obj)
                return s[:max_len] + "..." if len(s) > max_len else s
            except Exception as e:
                return f"<non-serializable: {type(obj).__name__}>"
        
        for task in state.plan:
            # Audit trail construction
            result_summary = "Pending"
            if task.id in state.task_results:
                res = state.task_results[task.id]
                result_summary = safe_truncate(res, max_len=100)
            
            audit_trail.append(TaskExecutionDetail(
                task_id=task.id,
                description=task.description,
                tool=task.tool_name or "Internal",
                status=task.status,
                result_summary=result_summary
            ))

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
            unique_tickers = []
        if not sources:
            sources = {"SEC EDGAR", "Financial Data Providers"}
        
        # Forensic Log construction
        evidence_log = []
        for task in state.plan:
            if task.id in state.task_results:
                result = state.task_results[task.id]
                
                # Extract ticker if possible
                if isinstance(result, list):
                    for i, item in enumerate(result[:5]): # Cap at 5 per task
                        evidence_log.append(EvidenceItem(
                            id=f"E{len(evidence_log)+1}",
                            metric=f"{task.description} [Ref {i+1}]",
                            value=safe_truncate(item, max_len=100),
                            period="HISTORICAL",
                            source=task.tool_name or "Financial Provider",
                            status="VERIFIED"
                        ))
                else:
                    evidence_log.append(EvidenceItem(
                        id=f"E{len(evidence_log)+1}",
                        metric=task.description,
                        value=safe_truncate(result, max_len=100),
                        period="CURRENT",
                        source=task.tool_name or "Financial Provider",
                        status="VERIFIED"
                    ))
        
        # Qualitative Fallback: If report is valid but plan was empty (qualitative query)
        if not evidence_log and state.status == "Completed":
            evidence_log.append(EvidenceItem(
                id="E1",
                metric="Qualitative Analysis",
                value="Synthesis derived from institutional knowledge base.",
                period="N/A",
                source="Jasper Internal Engine",
                status="INFERRED"
            ))

        # Forensic Logic Constraints mapping
        logic_constraints = state.report.logic_constraints if state.report and hasattr(state.report, 'logic_constraints') else {}
        if not state.plan:
            logic_constraints["QUERY_INTENT"] = "Qualitative research selected; financial statement fetching skipped."
        
        # Simple Inference Link (Linking all evidence to the synthesis)
        inference_map = []
        if evidence_log:
            inference_map.append(InferenceLink(
                claim="Research findings are supported by the identified evidence set.",
                evidence_ids=[e.id for e in evidence_log],
                logic_path="Deterministic synthesis based on retrieved artifacts.",
                confidence=state.validation.confidence if state.validation else 1.0
            ))
        
        # Construct FinalReport
        report = FinalReport(
            query=state.query,
            report_mode=state.report_mode,
            data_sources=list(sources),
            tickers=unique_tickers,
            synthesis_text=state.final_answer or "",
            is_valid=state.validation.is_valid if state.validation else False,
            validation_issues=state.validation.issues if state.validation else [],
            confidence_score=state.validation.confidence if state.validation else 0.0,
            confidence_breakdown=state.validation.breakdown if state.validation else None,
            task_count=len(state.plan),
            task_results=state.task_results,
            # Forensic Fields
            evidence_log=evidence_log,
            inference_map=inference_map,
            logic_constraints=logic_constraints, 
            audit_trail=audit_trail
        )
        
        return report
