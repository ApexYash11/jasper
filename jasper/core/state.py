from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum

# --- Report Modes ---
class ReportMode(str, Enum):
    BUSINESS_MODEL = "business_model"
    RISK_ANALYSIS = "risk_analysis"
    FINANCIAL_EVIDENCE = "financial_evidence"
    GENERAL = "general"

# Schema definitions for Jasper's internal state management
class Task(BaseModel):
    id: str = Field(..., description="Unique identifier for the task")
    description: str = Field(..., description="Description of the task")
    tool_name: Optional[str] = Field(default=None, description="Name of the tool to be used for the task")
    tool_args: Optional[Dict[str, Any]] = Field(default=None, description="Arguments for the tool")
    status: Literal["pending", "in_progress", "completed", "failed"] = Field(default="pending", description="Current status of the task")
    error: Optional[str] = Field(default=None, description="Error message if the task failed")

# --- Confidence Breakdown ---
# Provides a detailed view of the confidence score components
class ConfidenceBreakdown(BaseModel):
    data_coverage: float      # % of required data fetched
    data_quality: float       # provider reliability
    inference_strength: float # logic depth
    overall: float

# --- Forensic Models ---
class EvidenceItem(BaseModel):
    id: str = Field(..., description="Evidence ID (e.g., E1.1)")
    metric: str = Field(..., description="Financial metric or data point")
    value: Any = Field(..., description="The value of the metric")
    period: str = Field(..., description="Time period for the value")
    source: str = Field(..., description="Data provider source")
    status: str = Field(default="VERIFIED", description="Verification status")

class InferenceLink(BaseModel):
    claim: str = Field(..., description="The analytical claim being made")
    evidence_ids: List[str] = Field(..., description="List of evidence IDs supporting this claim")
    logic_path: str = Field(..., description="Brief description of the logic used")
    confidence: float = Field(default=1.0, description="Confidence in this specific inference")

class TaskExecutionDetail(BaseModel):
    task_id: str
    description: str
    tool: str
    status: str
    result_summary: str

class validationresult(BaseModel):
    is_valid: bool = Field(..., description="Indicates if the state is valid")
    issues: List[str] = Field(default_factory=list, description="List of issues found during validation")
    confidence: float = Field(default=0.0, description="Confidence score of the validation result")
    breakdown: Optional[ConfidenceBreakdown] = Field(default=None, description="Detailed confidence breakdown")


# --- Final Report ---
# Single source of truth for audit-ready PDF exports
class FinalReport(BaseModel):
    """Audit-ready financial research report for PDF export."""
    
    # Metadata
    query: str = Field(..., description="Original user query")
    report_mode: ReportMode = Field(default=ReportMode.GENERAL, description="The inferred analytical mode of the report")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp (UTC)")
    version: str = Field(default="0.2.0", description="Jasper version at report generation time")
    
    # Data sourcing
    data_sources: List[str] = Field(default_factory=list, description="List of data providers used (e.g., ['yfinance', 'Alpha Vantage'])")
    tickers: List[str] = Field(default_factory=list, description="Financial instruments analyzed")
    
    # Forensic Evidence & Analysis
    evidence_log: List[EvidenceItem] = Field(default_factory=list, description="Structured log of all evidence artifacts")
    inference_map: List[InferenceLink] = Field(default_factory=list, description="Map of claims to their supporting evidence")
    logic_constraints: Dict[str, str] = Field(default_factory=dict, description="Constraints applied during synthesis (e.g. data gaps)")
    audit_trail: List[TaskExecutionDetail] = Field(default_factory=list, description="Forensic audit of execution steps")
    
    # Results (Legacy/Secondary)
    synthesis_text: str = Field(..., description="Final synthesized analysis (markdown or plain text)")
    
    # Validation & confidence
    is_valid: bool = Field(..., description="Whether validation passed")
    validation_issues: List[str] = Field(default_factory=list, description="Validation issues encountered")
    confidence_score: float = Field(default=0.0, description="Overall confidence (0.0-1.0)")
    confidence_breakdown: Optional[ConfidenceBreakdown] = Field(default=None, description="Detailed confidence breakdown")
    
    # Task execution details for audit trail
    task_count: int = Field(default=0, description="Number of execution tasks")
    task_results: Dict[str, Any] = Field(default_factory=dict, description="Raw task execution results")


class Jasperstate(BaseModel):
    query: str = Field(..., description="The original user query")
    report_mode: ReportMode = Field(default=ReportMode.GENERAL, description="The inferred analytical mode of the report")

    plan: List[Task] = Field(default_factory=list, description="List of tasks in the plan")
    current_task_index: int = Field(default=0, description="Index of the current task being executed")

    task_results: Dict[str, Dict] = Field(default_factory=dict, description="Results of executed tasks, keyed by task ID")

    validation: Optional[validationresult] = Field(default=None, description="Validation result of the current state")

    retries: int = Field(default=0, description="Number of retries attempted for failed tasks")
    max_retries: int = Field(default=3, description="Maximum number of retries allowed for failed tasks")

    status: Literal["Planning", "Executing", "Validating", "Synthesizing", "Completed", "Failed"] = Field(default="Planning", description="Current status of the agent")

    final_answer: Optional[str] = Field(default=None, description="The final answer generated by Jasper")
    error: Optional[str] = Field(default=None, description="Error message if the run failed unexpectedly")
    error_source: Optional[str] = Field(default=None, description="Source of the error: 'data_provider', 'llm_service', 'llm_auth', 'llm_timeout', 'llm_unknown', or 'query'")
    
    # Report object (populated after synthesis)
    report: Optional[FinalReport] = Field(default=None, description="Audit-ready report for export")
