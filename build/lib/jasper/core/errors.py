"""Jasper domain exception hierarchy.

All Jasper-specific errors derive from JasperError so callers can
catch the base class when they don't need fine-grained handling.
"""


class JasperError(Exception):
    """Base exception for all Jasper domain errors."""


class EntityExtractionError(JasperError):
    """Raised when entity extraction fails to parse a query."""


class PlannerError(JasperError):
    """Raised when the planner fails to generate a valid plan."""


class DataFetchError(JasperError):
    """Raised when all data providers fail to fetch requested data."""


class SynthesisError(JasperError):
    """Raised when the synthesizer fails to generate the final report."""


class ValidationError(JasperError):
    """Raised when report validation fails after all retry attempts."""


class ConfigurationError(JasperError):
    """Raised when required configuration (API keys, settings) is missing or invalid."""
