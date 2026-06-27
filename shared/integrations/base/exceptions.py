"""Base integration exceptions."""


class IntegrationError(Exception):
    """Base exception for all integration errors."""


class IntegrationConnectionError(IntegrationError):
    """Connection to external service failed."""


class IntegrationAuthenticationError(IntegrationError):
    """Authentication with external service failed."""


class IntegrationTimeoutError(IntegrationError):
    """Request to external service timed out."""
