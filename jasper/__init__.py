__version__ = "1.0.9"

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .core.state import FinalReport

__all__ = ["run_research", "__version__"]


async def run_research(query: str) -> "Optional[FinalReport]":
    """
    Public Python API for programmatic / notebook usage.

    Runs a full Jasper research pipeline and returns a structured FinalReport.

    Example::

        import asyncio
        from jasper import run_research

        report = asyncio.run(run_research("What is Apple's revenue trend?"))
        if report:
            print(report.synthesis_text)
            print(report.confidence_score)

    Args:
        query: A natural-language financial research question.

    Returns:
        A :class:`~jasper.core.state.FinalReport` Pydantic model, or ``None``
        if the pipeline failed (check ``state.error`` for details).
    """
    import os
    from .core.controller import JasperController
    from .agent.planner import Planner
    from .agent.executor import Executor
    from .agent.validator import validator as ValidatorClass
    from .agent.synthesizer import Synthesizer
    from .tools.financials import FinancialDataRouter
    from .tools.providers.alpha_vantage import AlphaVantageClient
    from .tools.providers.yfinance import YFinanceClient
    from .core.llm import get_llm

    llm = get_llm(temperature=0)
    av_client = AlphaVantageClient(api_key=os.getenv("ALPHA_VANTAGE_API_KEY", "demo"))
    yf_client = YFinanceClient()
    router = FinancialDataRouter(providers=[av_client, yf_client])

    controller = JasperController(
        planner=Planner(llm),
        executor=Executor(router),
        validator=ValidatorClass(),
        synthesizer=Synthesizer(llm),
    )

    state = await controller.run(query)
    return state.report


# Lazy import so `from jasper import FinalReport` works without pulling
# the entire dependency tree at import time.
def __getattr__(name: str):
    if name == "FinalReport":
        from .core.state import FinalReport
        return FinalReport
    raise AttributeError(f"module 'jasper' has no attribute {name!r}")

