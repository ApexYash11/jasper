import os
import sys
from pathlib import Path
from datetime import datetime
from jasper.core.state import FinalReport, ConfidenceBreakdown, ReportMode, EvidenceItem, InferenceLink, TaskExecutionDetail
from jasper.export.pdf import export_report_to_pdf

def generate_sample_report():
    # 1. Create forensic mock data
    report = FinalReport(
        query="What is the intrinsic value and market risk of NVDA (NVIDIA) in early 2026?",
        report_mode=ReportMode.RISK_ANALYSIS,
        synthesis_text="""
## Analytical Narrative
NVIDIA continues to dominate the accelerated computing market with a **92% market share** in data center GPUs. 
The transition to the Blackwell architecture has solidified its competitive moat. 
However, high concentration in APAC manufacturing remains a critical structural risk.
        """,
        is_valid=True,
        confidence_score=0.94,
        confidence_breakdown=ConfidenceBreakdown(
            data_coverage=0.98,
            data_quality=0.95,
            inference_strength=0.90,
            overall=0.94
        ),
        tickers=["NVDA"],
        data_sources=["AlphaVantage", "SEC Edgar", "YFinance"],
        version="0.2.0",
        
        # --- NEW FORENSIC FIELDS ---
        evidence_log=[
            EvidenceItem(id="E1.1", metric="Data Center Revenue", value=".5B", period="FY2025", source="SEC Edgar", status="VERIFIED"),
            EvidenceItem(id="E1.2", metric="Gross Margin", value="76.4%", period="Q3 2025", source="SEC Edgar", status="VERIFIED"),
            EvidenceItem(id="E2.1", metric="GPU Market Share", value="92%", period="2025", source="AlphaVantage", status="VERIFIED"),
        ],
        inference_map=[
            InferenceLink(
                claim="Dominant market position in AI hardware.",
                evidence_ids=["E2.1", "E1.1"],
                logic_path="Market Share > 90% + Revenue Growth > 100% YoY",
                confidence=0.98
            ),
            InferenceLink(
                claim="Pricing power remains exceptionally strong.",
                evidence_ids=["E1.2"],
                logic_path="Margins sustained at >75% despite competition",
                confidence=0.95
            )
        ],
        logic_constraints={
            "Market Scope": "Valuation mechanics are out of scope for this mode.",
            "Data Latency": "Report relies on public SEC filings with T-30 latency.",
            "Geopolitical": "Supply chain risk assessed via public logistics maps only."
        },
        audit_trail=[
            TaskExecutionDetail(task_id="T1", description="Fetch NVDA 10-K filings", tool="SEC Edgar", status="SUCCESS", result_summary="Found FY2025 revenue metrics"),
            TaskExecutionDetail(task_id="T2", description="Analyze market share data", tool="AlphaVantage", status="SUCCESS", result_summary="Confirmed 92% GPU dominance"),
        ]
    )

    # 2. Define output path
    output_dir = Path("exports")
    output_dir.mkdir(exist_ok=True)
    pdf_path = output_dir / "judgment_report_forensic.pdf"

    print(f"Generating Forensic Artifact for: {report.query}...")
    
    try:
        # 3. Export
        result_path = export_report_to_pdf(report, str(pdf_path))
        print(f"SUCCESS: Forensic Artifact generated at {result_path}")
        return result_path
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAILED: {str(e)}")
        return None

if __name__ == "__main__":
    generate_sample_report()
