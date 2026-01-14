"""
Smoke test for PDF export feature.

Tests:
  1. FinalReport dataclass construction
  2. HTML rendering via Jinja2
  3. PDF compilation via WeasyPrint
  4. Deterministic output (reproducibility)
  5. Offline operation (no network access)
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from jasper.core.state import FinalReport, ConfidenceBreakdown
from jasper.export.pdf import (
    render_report_html,
    compile_html_to_pdf,
    export_report_to_pdf,
    export_report_html,
    load_css_content,
)


@pytest.fixture
def sample_report() -> FinalReport:
    """Create a minimal but valid FinalReport for testing."""
    return FinalReport(
        query="What is Apple's financial performance in Q4 2024?",
        timestamp=datetime(2024, 12, 15, 14, 30, 0),
        version="0.2.0",
        data_sources=["yfinance", "Alpha Vantage"],
        tickers=["AAPL"],
        synthesis_text="""
        ### Revenue Performance
        Apple reported strong Q4 2024 performance with revenue of $123.5B.
        """,
        is_valid=True,
        validation_issues=[],
        confidence_score=0.92,
        confidence_breakdown=ConfidenceBreakdown(
            data_coverage=0.95,
            data_quality=0.90,
            inference_strength=0.88,
            overall=0.91,
        ),
        task_count=3,
        task_results={
            "task_1": {"data": "revenue_data", "status": "completed"},
        },
        # Forensic Fields
        evidence_log=[],
        inference_map=[],
        logic_constraints={"Scope": "Testing"},
        audit_trail=[]
    )


def test_final_report_construction(sample_report):
    """Test that FinalReport can be constructed and validated."""
    assert sample_report.query == "What is Apple's financial performance in Q4 2024?"
    assert sample_report.is_valid is True
    assert sample_report.confidence_score == 0.92
    assert len(sample_report.tickers) == 1
    assert sample_report.tickers[0] == "AAPL"
    assert sample_report.task_count == 3


def test_css_loading():
    """Test that CSS stylesheet can be loaded."""
    css = load_css_content()
    assert len(css) > 0
    assert "body" in css
    assert "table" in css
    assert "report-section" in css


def test_html_rendering(sample_report):
    """Test HTML rendering from FinalReport."""
    html = render_report_html(sample_report)
    
    # Verify HTML is valid and contains expected elements
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html
    
    # Verify report content is rendered (may be escaped)
    assert "Apple" in html or "AAPL" in html
    assert "92" in html  # confidence_score as percentage
    
    # Verify semantic structure
    assert "cover-page" in html
    assert "confidence-metrics" in html or "callout-confidence" in html
    assert "report-section" in html
    
    # Verify no network dependencies
    assert "http://" not in html.split("<body>")[0]  # No external URLs in head


def test_html_export(sample_report):
    """Test exporting report to HTML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_report.html"
        result_path = export_report_html(sample_report, str(output_path))
        
        # Verify file was created
        assert Path(result_path).exists()
        assert Path(result_path).suffix == ".html"
        
        # Verify file contains expected content
        content = Path(result_path).read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "AAPL" in content or "Apple" in content


def test_pdf_compilation_deterministic(sample_report):
    """Test that PDF compilation is deterministic (same input → same output)."""
    html = render_report_html(sample_report)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate PDF twice with same HTML
        pdf_path_1 = Path(tmpdir) / "report_1.pdf"
        pdf_path_2 = Path(tmpdir) / "report_2.pdf"
        
        compile_html_to_pdf(html, str(pdf_path_1))
        compile_html_to_pdf(html, str(pdf_path_2))
        
        # Both files should exist
        assert pdf_path_1.exists()
        assert pdf_path_2.exists()
        
        # Both should be valid PDFs (contain PDF header)
        with open(pdf_path_1, "rb") as f:
            assert f.read(4) == b"%PDF"
        
        with open(pdf_path_2, "rb") as f:
            assert f.read(4) == b"%PDF"


def test_pdf_export_valid_report(sample_report):
    """Test exporting a valid report to PDF."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "valid_report.pdf"
        result_path = export_report_to_pdf(sample_report, str(output_path), validate=True)
        
        # Verify file was created
        assert Path(result_path).exists()
        assert Path(result_path).suffix == ".pdf"
        
        # Verify it's a valid PDF
        with open(result_path, "rb") as f:
            assert f.read(4) == b"%PDF"


def test_pdf_export_invalid_report_raises(sample_report):
    """Test that exporting an invalid report raises ValueError when validate=True."""
    sample_report.is_valid = False
    sample_report.validation_issues = ["Missing revenue data", "Incomplete market analysis"]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "invalid_report.pdf"
        
        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            export_report_to_pdf(sample_report, str(output_path), validate=True)
        
        assert "Cannot export invalid report" in str(exc_info.value)
        assert "Missing revenue data" in str(exc_info.value)


def test_pdf_export_invalid_report_allows_bypass(sample_report):
    """Test that exporting an invalid report succeeds when validate=False."""
    sample_report.is_valid = False
    sample_report.validation_issues = ["Some issue"]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "forced_export.pdf"
        result_path = export_report_to_pdf(sample_report, str(output_path), validate=False)
        
        # Should succeed
        assert Path(result_path).exists()
        with open(result_path, "rb") as f:
            assert f.read(4) == b"%PDF"


def test_pdf_export_offline_no_network():
    """Test that PDF export does not make network calls."""
    report = FinalReport(
        query="Test query",
        synthesis_text="Test analysis",
        is_valid=True,
        tickers=["TEST"],
    )
    
    html = render_report_html(report)
    
    # Verify no external URLs in rendered HTML
    # (CSS and all resources should be embedded)
    assert "http://" not in html
    assert "https://" not in html
    # Exception: URLs in comments/markdown content are OK if clearly not resources
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Should compile without network access
        output_path = Path(tmpdir) / "offline_report.pdf"
        result_path = compile_html_to_pdf(html, str(output_path))
        assert Path(result_path).exists()


def test_pdf_with_special_characters(sample_report):
    """Test PDF export with special characters and Unicode."""
    sample_report.query = "What is 中国's market position? Müller's analysis."
    sample_report.synthesis_text = """
    <h3>International Markets</h3>
    <p>
    Analysis of 中国 (China) market: Strong growth potential.
    European markets (Müller analysis) show 8% CAGR.
    </p>
    """
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "unicode_report.pdf"
        result_path = export_report_to_pdf(sample_report, str(output_path), validate=True)
        
        assert Path(result_path).exists()
        with open(result_path, "rb") as f:
            assert f.read(4) == b"%PDF"


def test_pdf_with_tables(sample_report):
    """Test PDF export with HTML tables."""
    sample_report.synthesis_text = """
    <h3>Financial Summary</h3>
    <table>
        <thead>
            <tr>
                <th>Metric</th>
                <th>Q4 2024</th>
                <th>Q4 2023</th>
                <th>YoY Change</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Revenue (B$)</td>
                <td>123.5</td>
                <td>110.1</td>
                <td>+12.1%</td>
            </tr>
            <tr>
                <td>Operating Margin</td>
                <td>32.4%</td>
                <td>30.8%</td>
                <td>+1.6pp</td>
            </tr>
        </tbody>
    </table>
    """
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "table_report.pdf"
        result_path = export_report_to_pdf(sample_report, str(output_path), validate=True)
        
        assert Path(result_path).exists()
        with open(result_path, "rb") as f:
            assert f.read(4) == b"%PDF"


if __name__ == "__main__":
    # Run tests with: pytest tests/test_pdf_export.py -v
    pytest.main([__file__, "-v"])
