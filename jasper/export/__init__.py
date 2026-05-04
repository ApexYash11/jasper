"""
Export module for Jasper Finance.

Provides deterministic, audit-ready PDF generation from FinalReport objects.
"""

from .pdf import (
    export_report_to_pdf,
    export_report_html,
    merge_pdf_reports,
    verify_pdf_integrity,
    add_pdf_metadata,
)

__all__ = [
    "export_report_to_pdf",
    "export_report_html",
    "merge_pdf_reports",
    "verify_pdf_integrity",
    "add_pdf_metadata",
]
