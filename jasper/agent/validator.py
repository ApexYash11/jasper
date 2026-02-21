from ..core.state import Jasperstate, validationresult, ConfidenceBreakdown
from ..observability.logger import SessionLogger


class validator:
    def __init__(self, logger: SessionLogger | None = None):
        self.logger = logger or SessionLogger()

    def validate(self, state: Jasperstate) -> validationresult:
        self.logger.log("VALIDATION_STARTED", {"plan_length": len(state.plan)})
        issues = []
        hard_failures = []  # task errors that can never be recovered

        # 1. Task completion AND error checking
        for task in state.plan:
            if task.status != "completed":
                issues.append(f"Incomplete task: {task.description}")

            if task.error:
                hard_failures.append(f"Task error: {task.description} - {task.error}")

        # 2. Data sanity checks
        for task in state.plan:
            if task.id not in state.task_results:
                if task.status == "completed":
                    issues.append(f"Missing data for completed task: {task.description}")
            elif not state.task_results[task.id]:
                issues.append(f"Empty data for task: {task.description}")

        # 3. Financial logic checks
        self._validate_financial_consistency(state, issues)

        # --- Partial success path ---
        # If >=50% of tasks completed, allow synthesis with partial confidence.
        completed_count = sum(1 for t in state.plan if t.status == "completed")
        total_count = len(state.plan)
        is_valid: bool

        if total_count == 0:
            # Qualitative query — no data tasks, always valid
            is_valid = True
        elif completed_count == total_count:
            is_valid = len(issues) == 0
        elif completed_count / total_count >= 0.5:
            # Partial success: enough data to synthesise with caveats
            is_valid = True
            issues = hard_failures  # Surface only hard failures, not missing tasks
            self.logger.log("VALIDATION_PARTIAL_SUCCESS", {
                "completed": completed_count, "total": total_count
            })
        else:
            is_valid = False
        
        # Calculate Confidence Breakdown
        # Handle case where plan is empty (qualitative queries with no financial data fetch)
        if not state.plan:
            # QUALITATIVE MODE: No financial data fetching occurred.
            data_coverage = 1.0
            data_quality = 0.85
            inference_strength = 0.8
        elif completed_count == total_count:
            # Full success
            data_coverage = 1.0
            data_quality = 1.0
            if state.task_results:
                qualities = []
                for res in state.task_results.values():
                    if isinstance(res, list):
                        qualities.append(min(1.0, len(res) / 3.0))
                    else:
                        qualities.append(0.5)
                data_quality = sum(qualities) / len(qualities)
            else:
                data_quality = 0.0
            inference_strength = 0.9 if is_valid else 0.7
        else:
            # Partial success — penalise proportionally
            data_coverage = completed_count / total_count
            data_quality = 0.7  # conservative for incomplete data
            inference_strength = 0.7

        # Calculate confidence
        # Major issues reduce confidence, but don't zero it out completely
        overall_confidence = round(data_coverage * data_quality * inference_strength, 2)
        
        breakdown = ConfidenceBreakdown(
            data_coverage=round(data_coverage, 2),
            data_quality=round(data_quality, 2),
            inference_strength=inference_strength,
            overall=overall_confidence
        )

        result = validationresult(
            is_valid=is_valid,
            issues=issues,
            confidence=overall_confidence,
            breakdown=breakdown
        )

        self.logger.log("VALIDATION_COMPLETED", {"is_valid": result.is_valid, "issues": result.issues, "confidence": overall_confidence})
        return result

    def _validate_financial_consistency(self, state: Jasperstate, issues: list):
        # Example: revenue must be non-negative
        for result in state.task_results.values():
            # Assuming result might be a list of reports or a single report
            reports = result if isinstance(result, list) else [result]
            for report in reports:
                if isinstance(report, dict):
                    revenue = report.get("totalRevenue")
                    if revenue is not None:
                        try:
                            if float(revenue) < 0:
                                issues.append("Negative revenue detected")
                        except (ValueError, TypeError):
                            pass
