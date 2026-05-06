# Testing Jasper PDF Export Features

## Quick Start

### 1. Test Basic Export (with new metadata & verification)
```powershell
cd c:\Users\ACER\OneDrive\Documents\GitHub\jasper
.\.venv\Scripts\jasper export "What is Apple's revenue trend?"
```
This will:
- Generate a research report
- **NEW:** Inject PDF metadata (Title, Subject, Author, Keywords)
- **NEW:** Verify PDF integrity and log any issues
- Save to `exports/jasper_report_YYYYMMDD_HHMMSS.pdf`

### 2. Check PDF Metadata
Open the generated PDF in Adobe Reader/Preview:
1. Right-click the PDF → "Properties" / "Get Info"
2. Go to "Details" / "Description" tab
3. You'll see:
   - **Title:** "Jasper Analysis: What is Apple's revenue..."
   - **Subject:** "AAPL - financial_evidence"
   - **Author:** "Jasper Finance v1.1.6"
   - **Keywords:** "AAPL, yfinance, Alpha Vantage"

### 3. Test Single Query (One-off)
```powershell
.\.venv\Scripts\jasper ask "Analyze Tesla operating margins"
```

### 4. Test Interactive Mode (Session Memory)
```powershell
.\.venv\Scripts\jasper interactive
# Then type queries like:
# Query 1: "What is Microsoft's revenue?"
# Query 2: "and what about their cash flow?"  (uses previous context)
```

### 5. Test Batch Merge (NEW - Python API)
```powershell
.\.venv\Scripts\python
```

```python
import asyncio
from jasper import run_research
from jasper.export import export_report_to_pdf, merge_pdf_reports


async def main():
    # Generate 2 reports
    report1 = await run_research("Apple revenue trend")
    report2 = await run_research("Microsoft revenue trend")

    # Export both
    pdf1 = export_report_to_pdf(report1, "exports/report_apple.pdf", validate=True)
    pdf2 = export_report_to_pdf(report2, "exports/report_microsoft.pdf", validate=True)

    # Merge them
    merged_pdf = merge_pdf_reports(
        [pdf1, pdf2],
        "exports/merged_analysis.pdf",
        tickers=["AAPL", "MSFT"]
    )

    print(f"✅ Merged PDF: {merged_pdf}")


asyncio.run(main())
```

---

## Verify New Features

### Feature 1: Metadata Injection ✅
```powershell
# Generate a PDF export
.\.venv\Scripts\jasper export "Apple revenue"

# Verify metadata injection with Python
.\.venv\Scripts\python
```

```python
from pypdf import PdfReader
from glob import glob

pdf_files = sorted(glob("exports/jasper_report_*.pdf"))
if not pdf_files:
    raise FileNotFoundError("No PDF files found in exports/")

pdf_path = pdf_files[-1]
reader = PdfReader(pdf_path)
metadata = reader.metadata

print("PDF Metadata:")
print(f"  Title: {metadata.get('/Title')}")
print(f"  Subject: {metadata.get('/Subject')}")
print(f"  Author: {metadata.get('/Author')}")
print(f"  Keywords: {metadata.get('/Keywords')}")
```

### Feature 2: ReportLab Fallback Renderer ✅
```powershell
# Run tests to verify ReportLab is working
.\.venv\Scripts\pytest tests/test_pdf_export.py::test_reportlab_fallback_compile -v
```

Expected output: `PASSED` (PDF generated successfully with ReportLab)

### Feature 3: PDF Integrity Verification ✅
```powershell
.\.venv\Scripts\pytest tests/test_pdf_export.py::test_pdf_integrity_verification_extractable -v
```

Expected output: `PASSED` (PDF content verified as extractable)

### Feature 4: Batch Merging ✅
```powershell
.\.venv\Scripts\pytest tests/test_pdf_export.py::test_batch_merge_pdfs -v
```

Expected output: `PASSED` (Multiple PDFs merged successfully)

---

## Run All PDF Tests
```powershell
.\.venv\Scripts\pytest tests/test_pdf_export.py -v
```

Expected: All 19 tests passing ✅

---

## What to Expect

### Before (v1.1.6 without enhancements)
```
jasper export "Apple revenue"
✅ exports/jasper_report_20260503_143012.pdf
   - Basic PDF generated
   - No metadata
   - Limited error recovery
```

### After (v1.1.6 with enhancements)
```
jasper export "Apple revenue"
✅ Rendering HTML → PDF (WeasyPrint)
✅ Injecting metadata (Title, Subject, Author, Keywords, CreationDate)
✅ Verifying PDF integrity (page count, content extraction)
✅ exports/jasper_report_20260503_143012.pdf

📋 PDF Properties now include:
   - Title: "Jasper Analysis: What is Apple's revenue..."
   - Subject: "AAPL - financial_evidence"
   - Author: "Jasper Finance v1.1.6"
   - Keywords: "AAPL, yfinance"
```

---

## Troubleshooting

### Issue: "WeasyPrint unavailable"
This is normal on Windows! ReportLab will be used as fallback.
- PDF will render with ReportLab (same output, slightly simpler styling)
- You'll see warning: "⚠️  WeasyPrint unavailable. Trying ReportLab renderer..."
- This is **expected behavior** ✅

### Issue: "pdfplumber not available"
```powershell
.\.venv\Scripts\pip install pdfplumber
```

### Issue: API key not set
```powershell
$env:OPENROUTER_API_KEY="your-key-here"
$env:ALPHA_VANTAGE_API_KEY="your-key-here"
.\.venv\Scripts\jasper doctor
```

---

## New Functions (Python API)

All new functions are now available:

```python
from jasper.export import (
    add_pdf_metadata,
    verify_pdf_integrity,
    compile_html_to_pdf_reportlab,
    merge_pdf_reports,
)

# Add metadata to existing PDF
add_pdf_metadata("report.pdf", final_report)

# Verify a PDF after generation
is_valid, issues = verify_pdf_integrity("report.pdf", final_report)

# Use ReportLab directly (fallback)
compile_html_to_pdf_reportlab(html_content, "output.pdf")

# Merge multiple reports
merge_pdf_reports(
    ["report1.pdf", "report2.pdf"],
    "merged.pdf",
    tickers=["AAPL", "MSFT"]
)
```
