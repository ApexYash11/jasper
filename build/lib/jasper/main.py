"""
jasper/main.py — Convenience re-export for programmatic usage.

The CLI entry point lives in jasper/__main__.py.
The public Python API is exposed from jasper/__init__.py.

Usage (programmatic)::

    from jasper import run_research
    import asyncio
    report = asyncio.run(run_research("What is Apple's revenue trend?"))
"""

from jasper import run_research, __version__

__all__ = ["run_research", "__version__"]

