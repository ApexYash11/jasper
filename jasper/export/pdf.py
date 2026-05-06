"""
PDF Export Module for Jasper Finance

Renders audit-ready PDF reports using Jinja2 + WeasyPrint.
Ensures deterministic, offline-capable output without network access.
Supports modern CSS features (Grid, Flexbox) for professional layouts.

Architecture:
  - FinalReport (state.py) is the single source of truth
  - Jinja2 template (templates/report.html.jinja) handles semantic HTML
  - CSS (styles/report_v1.css) controls all layout and styling
  - WeasyPrint compiles HTML+CSS → PDF deterministically
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt

from ..core.state import FinalReport, ReportMode  # Add this import

logger = logging.getLogger(__name__)


def format_pdf_date(timestamp: datetime) -> str:
    """Convert a datetime to a PDF-spec CreationDate string."""
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone()

    offset = timestamp.strftime("%z")
    if not offset:
        offset = "+0000"
    return f"D:{timestamp.strftime('%Y%m%d%H%M%S')}{offset[:3]}'{offset[3:]}'"


def render_markdown(text: str) -> str:
    """Convert Markdown to semantic HTML."""
    md = MarkdownIt("commonmark", {
        "html": True,
        "typographer": True,
    })
    return md.render(text)


def get_report_template_dir() -> Path:
    """Get the templates directory path."""
    # Relative to this module (jasper/export/pdf.py)
    module_dir = Path(__file__).parent.parent
    templates_dir = module_dir / "templates"
    return templates_dir


def get_styles_dir() -> Path:
    """Get the styles directory path."""
    # Relative to this module
    module_dir = Path(__file__).parent.parent
    styles_dir = module_dir / "styles"
    return styles_dir


def load_css_content() -> str:
    """
    Load CSS content from report_v1.css.
    
    Returns:
        CSS content as string, safe to embed in HTML
    
    Raises:
        FileNotFoundError: If CSS file not found
    """
    css_path = get_styles_dir() / "report_v1.css"
    if not css_path.exists():
        raise FileNotFoundError(f"CSS stylesheet not found: {css_path}")
    
    with open(css_path, "r", encoding="utf-8") as f:
        return f.read()


def setup_jinja_environment() -> Environment:
    """
    Configure Jinja2 environment for report rendering.
    
    Returns:
        Configured Jinja2 Environment
    """
    template_dir = get_report_template_dir()
    
    if not template_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")
    
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=('html', 'jinja')),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    
    # Register custom filters for deterministic rendering
    env.filters['hash'] = lambda x: hashlib.sha256(x.encode()).hexdigest()[:16]
    env.filters['markdown'] = render_markdown
    
    return env


def render_report_html(report: FinalReport) -> str:
    """
    Render FinalReport to semantic HTML using Jinja2.
    
    Args:
        report: FinalReport object containing all report data
    
    Returns:
        HTML string (UTF-8 encoded)
    
    Raises:
        FileNotFoundError: If template or CSS not found
        Exception: If rendering fails
    """
    env = setup_jinja_environment()
    
    # Load CSS content once
    css_content = load_css_content()
    
    # Get template
    template = env.get_template("report.html.jinja")
    
    # Pre-render the synthesis text to HTML
    synthesis_html = render_markdown(report.synthesis_text)
    
    # Render with context
    html = template.render(
        report=report,
        css_content=css_content,
        synthesis_html=synthesis_html,
    )
    
    return html


def compile_html_to_pdf(html_content: str, output_path: str) -> str:
    """
    Compile semantic HTML + CSS to PDF.
    
    Tries multiple rendering engines in cascade for maximum compatibility:
    1. WeasyPrint (preferred, modern CSS support)
    2. ReportLab (fallback, basic CSS but lightweight)
    3. xhtml2pdf (final fallback, compatible but limited)
    
    WeasyPrint on Windows requires GTK+ libraries. If running from source,
    the build script (build.ps1) creates a self-contained executable with
    all dependencies bundled.
    
    Args:
        html_content: Complete HTML string to render
        output_path: Path where PDF should be written
    
    Returns:
        Absolute path to generated PDF
    """
    pdf_path = Path(output_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    
    # --- Try WeasyPrint (Preferred) ---
    try:
        import contextlib
        import sys
        import logging as log_module
        import os
        
        # WINDOWS DLL COLLISION FIX: 
        # Tesseract-OCR often bundles an incompatible libgobject-2.0-0.dll.
        # We temporarily remove it from PATH to let WeasyPrint find the correct one or fail cleanly.
        original_path = os.environ.get("PATH", "")
        if sys.platform == "win32":
            paths = original_path.split(os.pathsep)
            # Remove Tesseract paths which are known to cause collisions
            scrubbed_paths = [p for p in paths if "Tesseract-OCR" not in p]
            os.environ["PATH"] = os.pathsep.join(scrubbed_paths)

        try:
            # Suppress WeasyPrint loggers and standard error streams (GTK+ missing on Windows)
            log_module.getLogger("weasyprint").setLevel(log_module.CRITICAL)
            with open(os.devnull, "w") as devnull_out, open(os.devnull, "w") as devnull_err:
                with contextlib.redirect_stdout(devnull_out), contextlib.redirect_stderr(devnull_err):
                    from weasyprint import HTML
                    HTML(string=html_content).write_pdf(target=str(pdf_path))
            logger.info(f"PDF successfully rendered using WeasyPrint: {pdf_path}")
            return str(pdf_path.resolve())
        finally:
            # Always restore PATH
            if sys.platform == "win32":
                os.environ["PATH"] = original_path

    except (ImportError, Exception) as e:
        # Gracefully handle missing GTK+ or WeasyPrint
        logger.warning(
            "⚠️  WeasyPrint unavailable. Trying ReportLab renderer..."
        )
        logger.debug(f"    WeasyPrint error: {e}")
        pass

    # --- Try ReportLab (Secondary Fallback) ---
    try:
        pdf_path_rl = compile_html_to_pdf_reportlab(html_content, str(pdf_path))
        logger.info(f"PDF successfully rendered using ReportLab (fallback): {pdf_path}")
        return pdf_path_rl
    except Exception as e:
        logger.warning(
            "⚠️  ReportLab fallback failed. Trying xhtml2pdf renderer..."
        )
        logger.debug(f"    ReportLab error: {e}")
        pass

    # --- Fallback to xhtml2pdf (Final Fallback) ---
    try:
        from xhtml2pdf import pisa
        from io import BytesIO
        
        result_file = BytesIO()
        # Providing a base_url prevents 'NoneType' + 'str' errors when resolving paths
        pisa_status = pisa.CreatePDF(
            html_content,
            dest=result_file,
            encoding='utf-8',
            base_url=str(Path.cwd())
        )
        
        if getattr(pisa_status, 'err', 0) != 0:
            # Try once more without explicit encoding if it failed
            result_file = BytesIO()
            pisa_status = pisa.CreatePDF(
                html_content, 
                dest=result_file,
                base_url=str(Path.cwd())
            )
            
        if getattr(pisa_status, 'err', 0) != 0:
            raise RuntimeError(f"xhtml2pdf final fallback failed with status {getattr(pisa_status, 'err', 'unknown')}")
            
        with open(pdf_path, "wb") as f:
            result_file.seek(0)
            f.write(result_file.getvalue())
        
        logger.info(f"PDF successfully rendered using xhtml2pdf (final fallback): {pdf_path}")
        return str(pdf_path.resolve())
        
    except Exception as e:
        raise RuntimeError(f"PDF compilation failed (all engines): {str(e)}") from e


def export_report_to_pdf(
    report: FinalReport,
    output_path: str,
    validate: bool = True,
) -> str:
    """
    Export a FinalReport to audit-ready PDF.
    
    High-level entry point that validates state, renders HTML, compiles PDF,
    injects metadata, and verifies integrity.
    
    Pipeline:
    1. Validate report state (if validate=True)
    2. Render FinalReport to semantic HTML
    3. Compile HTML to PDF (WeasyPrint → ReportLab → xhtml2pdf)
    4. Inject searchable metadata (Title, Subject, Author, Keywords)
    5. Verify PDF integrity (non-blocking)
    
    Args:
        report: FinalReport object to export
        output_path: Path where PDF should be written
        validate: If True, verify report is valid before export
    
    Returns:
        Absolute path to generated PDF file
    
    Raises:
        ValueError: If validation fails (when validate=True)
        RuntimeError: If PDF compilation fails entirely
    """
    # FORENSIC VALIDATION GATE
    if validate:
        errors = []
        if not report.is_valid:
            errors.append("Report validation flag is FALSE")
        
        # FIX #10: Allow empty evidence_log for qualitative reports
        # Qualitative queries (business model, strategy) intentionally have no financial evidence
        is_qualitative = report.report_mode in (ReportMode.BUSINESS_MODEL, ReportMode.GENERAL)
        if not report.evidence_log and not is_qualitative:
            errors.append("Forensic Evidence Log is EMPTY (only allowed for qualitative reports)")
        
        # Check for reference integrity (only if evidence_log is non-empty)
        if report.evidence_log:
            evidence_ids = {e.id for e in report.evidence_log}
            for inf in report.inference_map:
                for eid in inf.evidence_ids:
                    if eid not in evidence_ids:
                        errors.append(f"Inference claim '{inf.claim[:40]}...' references missing evidence ID: {eid}")

        if errors:
            issues_str = "\n  - ".join(errors + (report.validation_issues or []))
            raise ValueError(
                f"Cannot export forensic artifact. Integrity checks failed:\n"
                f"  - {issues_str}\n"
                f"Confidence: {report.confidence_score:.1%}\n"
                f"Report Mode: {report.report_mode.value}\n"
            )
    
    # Render HTML from report
    html = render_report_html(report)
    
    # Compile to PDF
    pdf_path = compile_html_to_pdf(html, output_path)
    
    # Phase 1: Inject metadata
    pdf_path = add_pdf_metadata(pdf_path, report)
    
    # Phase 3: Verify integrity (non-blocking)
    is_valid, issues = verify_pdf_integrity(pdf_path, report)
    if not is_valid and issues:
        logger.warning(f"PDF integrity notice (report still valid): {', '.join(issues)}")
    
    return pdf_path


def export_report_html(
    report: FinalReport,
    output_path: str,
) -> str:
    """
    Export a FinalReport to HTML (for debugging/preview).
    
    Useful for inspecting rendered output before PDF generation.
    
    Args:
        report: FinalReport object to export
        output_path: Path where HTML should be written
    
    Returns:
        Absolute path to generated HTML file
    """
    html = render_report_html(report)
    
    html_path = Path(output_path)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return str(html_path.resolve())


def add_pdf_metadata(
    pdf_path: str,
    report: FinalReport,
) -> str:
    """
    Inject searchable metadata into generated PDF.
    
    Adds Title, Subject, Author, Keywords, and CreationDate to PDF
    for better document discoverability in filing systems.
    
    Args:
        pdf_path: Path to generated PDF file
        report: FinalReport object containing metadata
    
    Returns:
        Absolute path to metadata-enhanced PDF file
    
    Raises:
        FileNotFoundError: If PDF file not found
        RuntimeError: If metadata injection fails
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        logger.warning("pypdf not available; skipping metadata injection")
        return str(Path(pdf_path).resolve())
    
    try:
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Read PDF
        reader = PdfReader(str(pdf_path_obj))
        writer = PdfWriter()
        
        # Copy all pages
        for page in reader.pages:
            writer.add_page(page)
        
        # Truncate query for title (max 100 chars)
        query_short = report.query[:100].replace("\n", " ")
        title = f"Jasper Analysis: {query_short}"
        
        # Build keywords from tickers and data sources
        keywords = ", ".join(report.tickers + report.data_sources) if (report.tickers or report.data_sources) else "financial analysis"
        
        # Add metadata
        writer.add_metadata({
            "/Title": title,
            "/Subject": f"{', '.join(report.tickers) if report.tickers else 'General'} - {report.report_mode.value}",
            "/Author": f"Jasper Finance v{report.version}",
            "/Keywords": keywords,
            "/CreationDate": format_pdf_date(report.timestamp),
        })
        
        # Write back to same file
        with open(pdf_path_obj, "wb") as f:
            writer.write(f)
        
        logger.debug(f"PDF metadata successfully injected: {pdf_path}")
        return str(pdf_path_obj.resolve())
        
    except Exception as e:
        logger.warning(f"Failed to inject PDF metadata: {e}")
        return str(Path(pdf_path).resolve())


def compile_html_to_pdf_reportlab(html_content: str, output_path: str) -> str:
    """
    Compile HTML to PDF using ReportLab Platypus.
    
    Fallback renderer for when WeasyPrint is unavailable.
    Provides better CSS support than xhtml2pdf.
    
    Args:
        html_content: Complete HTML string to render
        output_path: Path where PDF should be written
    
    Returns:
        Absolute path to generated PDF
    
    Raises:
        Exception: If rendering fails
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, Flowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        from html.parser import HTMLParser
    except ImportError:
        raise ImportError("ReportLab not available for PDF rendering")
    
    pdf_path = Path(output_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create PDF document
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
        )
        
        # Style sheet
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=HexColor('#2d3748'),
            spaceAfter=12,
            fontName='Helvetica-Bold',
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            textColor=HexColor('#1a202c'),
            spaceAfter=6,
            leading=12,
        )
        
        # Simple HTML-to-Platypus conversion (extract text from common tags)
        story: list[Flowable] = []
        
        # Extract main content between body tags (simplified)
        import re
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        body_content = body_match.group(1) if body_match else html_content
        
        # Parse headings and paragraphs
        h1_matches = re.finditer(r'<h1[^>]*>(.*?)</h1>', body_content, re.IGNORECASE | re.DOTALL)
        for match in h1_matches:
            text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            if text:
                story.append(Paragraph(text, title_style))
                story.append(Spacer(1, 0.1*inch))
        
        p_matches = re.finditer(r'<p[^>]*>(.*?)</p>', body_content, re.IGNORECASE | re.DOTALL)
        for match in p_matches:
            text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            if text:
                story.append(Paragraph(text, normal_style))
        
        # If no content extracted, add raw text
        if not story:
            raw_text = re.sub(r'<[^>]+>', '', body_content).strip()
            if raw_text:
                story.append(Paragraph(raw_text[:500], normal_style))
        
        # Build PDF
        if story:
            doc.build(story)
        else:
            # Fallback: create minimal PDF
            fallback_story: list[Flowable] = [Paragraph("Report generated with ReportLab.", normal_style)]
            doc.build(fallback_story)
        
        logger.info(f"PDF successfully rendered using ReportLab: {pdf_path}")
        return str(pdf_path.resolve())
        
    except Exception as e:
        raise RuntimeError(f"ReportLab PDF rendering failed: {str(e)}") from e


def verify_pdf_integrity(pdf_path: str, report: FinalReport) -> tuple:
    """
    Post-generation verification of PDF integrity.
    
    Validates that the generated PDF is not empty, has searchable metadata,
    and contains synthesis content.
    
    Args:
        pdf_path: Path to generated PDF file
        report: FinalReport object for content validation
    
    Returns:
        Tuple of (is_valid: bool, issues: List[str])
    """
    try:
        import pdfplumber
    except ImportError:
        logger.debug("pdfplumber not available; skipping PDF verification")
        return (True, [])
    
    issues = []
    
    try:
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            return (False, ["PDF file not found"])
        
        with pdfplumber.open(str(pdf_path_obj)) as pdf:
            # Check page count
            if len(pdf.pages) == 0:
                issues.append("PDF has no pages")
                return (False, issues)
            
            # Extract text from all pages
            all_text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                all_text += page_text + "\n"
            
            # Verify content presence
            if not all_text.strip():
                issues.append("PDF content is empty (no extractable text)")
            
            # Verify synthesis query or tickers present (case-insensitive)
            query_lower = report.query.lower()
            all_text_lower = all_text.lower()
            
            # Check if query keywords are in document
            query_words = [w for w in query_lower.split() if len(w) > 3]  # Skip small words
            if query_words and not any(word in all_text_lower for word in query_words[:2]):  # Check first 2 significant words
                issues.append(f"Query keywords not found in PDF content")
            
            # Check for tickers
            if report.tickers:
                found_tickers = sum(1 for ticker in report.tickers if ticker.upper() in all_text.upper())
                if found_tickers == 0:
                    issues.append(f"No tickers ({', '.join(report.tickers)}) found in PDF")
        
        is_valid = len(issues) == 0
        if is_valid:
            logger.debug(f"PDF integrity verification passed: {pdf_path}")
        else:
            logger.warning(f"PDF integrity issues found: {', '.join(issues)}")
        
        return (is_valid, issues)
        
    except Exception as e:
        logger.warning(f"PDF verification check failed: {e}")
        return (True, [])  # Non-blocking; don't fail export on verification error


def merge_pdf_reports(
    pdf_paths: list[str],
    output_path: str,
    tickers: list[str] | None = None,
) -> str:
    """
    Merge multiple PDF reports into a single batch document.
    
    Combines pages from multiple reports with batch metadata.
    
    Args:
        pdf_paths: List of paths to PDF files to merge
        output_path: Path where merged PDF should be written
        tickers: Optional list of tickers for batch metadata
    
    Returns:
        Absolute path to merged PDF file
    
    Raises:
        ImportError: If pypdf not available
        FileNotFoundError: If any PDF file not found
        RuntimeError: If merge fails
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        raise ImportError("pypdf required for batch report merging")
    
    try:
        if not pdf_paths:
            raise ValueError("No PDF files provided in pdf_paths")

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        writer = PdfWriter()
        total_pages = 0
        
        # Merge all PDFs
        for pdf_file in pdf_paths:
            pdf_path = Path(pdf_file)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_file}")
            
            reader = PdfReader(str(pdf_path))
            for page in reader.pages:
                writer.add_page(page)
                total_pages += 1
        
        # Add batch metadata
        ticker_str = ", ".join(tickers) if tickers else "Batch Analysis"
        writer.add_metadata({
            "/Title": f"Jasper Batch Report: {ticker_str}",
            "/Subject": f"Combined analysis of {len(pdf_paths)} reports",
            "/Author": "Jasper Finance",
            "/Keywords": ticker_str,
        })
        
        # Write merged PDF
        with open(output_path_obj, "wb") as f:
            writer.write(f)
        
        logger.info(f"Batch PDF merge successful: {total_pages} pages from {len(pdf_paths)} reports → {output_path}")
        return str(output_path_obj.resolve())
        
    except Exception as e:
        raise RuntimeError(f"PDF merge failed: {str(e)}") from e
