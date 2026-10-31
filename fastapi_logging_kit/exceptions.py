"""Exceptions raised by ``fastapi_logging_kit``.

FastAPI has no equivalent of ``django.core.exceptions``, so the small
set of exception types the package needs is defined here.

"""


class FastLoggingError(Exception):
    """Base class for every exception raised by ``fastapi_logging_kit``."""


class ImproperlyConfigured(FastLoggingError):
    """Raised when the ``fastapi_logging_kit`` configuration is unusable.

    This mirrors ``django.core.exceptions.ImproperlyConfigured`` and is
    raised, for example, when the email notifier is enabled but the SMTP
    settings required to send mail are missing.

    """
