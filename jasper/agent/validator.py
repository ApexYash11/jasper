from ..core.state import Jasperstate, validationresult, ConfidenceBreakdown
from ..observability.logger import SessionLogger


class validator:
    def __init__(self, logger: SessionLogger | None = None):
        self.logger = logger or SessionLogger()

    def validate(self, state: Jasperstate) -> validationresult:
        self.logger.log("VALIDATION_STARTED", {"plan_length": len(state.plan)})
        issues = []

        # 1. Task completion AND error checking
        for task in state.plan:
            if task.status != "completed":
                issues.append(f"Incomplete task: {task.description}")
            
            if task.error:
                issues.append(f"Task error: {task.description} - {task.error}")

        # 2. Data sanity checks
        for task in state.plan:
            if task.id not in state.task_results:
                if task.status == "completed":
                    issues.append(f"Missing data for completed task: {task.description}")
            elif not state.task_results[task.id]:
                issues.append(f"Empty data for task: {task.description}")

        # 3. Financial logic checks
        self._validate_financial_consistency(state, issues)

        is_valid = len(issues) == 0
        
        # Calculate Confidence Breakdown
        data_coverage = len(state.task_results) / len(state.plan) if state.plan else 0.0
        
        data_quality = 1.0
        if state.task_results:
            qualities = []
            for res in state.task_results.values():
                if isinstance(res, list):
                    # Expecting at least 3 years for quality
                    qualities.append(min(1.0, len(res) / 3.0))
                else:
                    qualities.append(0.5)
            data_quality = sum(qualities) / len(qualities)
        else:
            data_quality = 0.0

        inference_strength = 0.9 if is_valid else 0.0
        overall_confidence = 0.0 if not is_valid else round(data_coverage * data_quality * inference_strength, 2)
        
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
