"""Custom exception types for lotto toolkit."""


class FetchError(RuntimeError):
    """Raised when a data source cannot be fetched or parsed."""


class NormalizationError(ValueError):
    """Raised when draw data cannot be normalized."""
