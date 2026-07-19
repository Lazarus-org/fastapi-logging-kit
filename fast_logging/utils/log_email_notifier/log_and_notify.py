import inspect
import logging
from typing import Any, Dict, Optional

from fast_logging.constants.log_format_options import FORMAT_OPTIONS
from fast_logging.handlers import EmailHandler
from fast_logging.settings.conf import LogConfig
from fast_logging.utils.get_conf import get_config, get_email_setting
from fast_logging.utils.log_email_notifier.notifier import send_email_async


def log_and_notify_admin(
    logger: logging.Logger,
    level: int,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a message and email it to the administrator.

    Args:
        logger (logging.Logger): The logger to emit the record through.
        level (int): The log level of the record.
        message (str): The message to log and send.
        extra (Optional[Dict[str, Any]]): Extra attributes for the
            LogRecord. A ``request`` key is used to enrich the email.

    Raises:
        ValueError: If the email notifier is disabled, if the record
            cannot be created from the supplied parameters, or if
            ADMIN_EMAIL is not configured.

    """
    # Get the caller's frame to capture the correct module, file, and line number
    frame = inspect.currentframe().f_back  # type: ignore
    email_notifier_enable = get_config().get("log_email_notifier_enable", False)

    if not email_notifier_enable:
        raise ValueError(
            "Email notifier is disabled. Please set the 'ENABLE' option to True in the 'LOG_EMAIL_NOTIFIER'"
            " of your fast_logging configuration to activate email notifications."
        )

    _format = get_config().get("log_email_notifier_log_format", FORMAT_OPTIONS[1])

    try:
        # create a LogRecord
        log_record = logger.makeRecord(
            name=logger.name,
            level=level,
            fn=frame.f_code.co_filename,  # type: ignore
            lno=frame.f_lineno,  # type: ignore
            msg=message,
            args=(),
            exc_info=None,
            func=frame.f_code.co_name,  # type: ignore
            extra=extra,
        )

        # Pass the LogRecord to the logger's handlers
        logger.handle(log_record)
    except (TypeError, AttributeError) as e:
        raise ValueError(
            f"Failed to log message due to invalid param. Original error: {e}"
        ) from e
    # Create a formatter instance and pass the email_notifier format
    formatter = logging.Formatter(LogConfig.resolve_format(_format))

    # Format the log message using the formatter
    formatted_message = formatter.format(log_record)

    request = extra.get("request") if extra else None

    # Render the email template with the formatted message
    email_body = EmailHandler.render_template(formatted_message, request)

    subject = f"New Log Record: {logging.getLevelName(level)}"
    admin_email = get_email_setting("ADMIN_EMAIL")
    if not admin_email:
        raise ValueError(
            "'ADMIN EMAIL' not provided, please provide 'ADMIN_EMAIL' in the EMAIL "
            "block of your fast_logging configuration"
        )

    send_email_async(subject, email_body, [admin_email])
