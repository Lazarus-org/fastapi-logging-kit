from datetime import datetime
from logging import Handler, LogRecord
from typing import Any, Optional

from fastapi_logging_kit.templating import render_to_string
from fastapi_logging_kit.utils.get_conf import get_email_setting, use_email_notifier_template
from fastapi_logging_kit.utils.log_email_notifier.notifier import send_email_async
from fastapi_logging_kit.utils.request import get_ip_address, get_user_agent


class EmailHandler(Handler):
    """A custom logging handler that sends log records via email.

    This handler formats log records, optionally renders them using an
    email template, and sends the resulting email to the administrator's
    email address defined in the ``EMAIL`` block of the ``fastapi_logging_kit``
    configuration.

    Methods:
    -------
        emit(record: LogRecord) -> None:
            Processes a log record and sends it via email to the administrator.

        render_template(log_entry: str, request: Optional[Any] = None, template_path: str = "email_notifier_template.html") -> str:
            Renders the email body using the provided log entry and optional request details.
            The rendered email includes the log message, the current date and time,
            the user's IP address, and browser information.

    """

    def emit(self, record: LogRecord) -> None:
        """Processes a log record and sends it via email.

        This method retrieves the request from the log record (if available), formats
        the log message, optionally renders the email body using a template, and sends
        the email asynchronously to the administrator.

        Args:
        ----
            record (LogRecord): The log record to be processed and sent via email.

        Raises:
        ------
            Exception: If any error occurs while sending the email or formatting the log record.

        """
        try:
            request = getattr(record, "request", None)
            log_entry = self.format(record)

            if use_email_notifier_template():
                email_body = self.render_template(log_entry, request)
            else:
                email_body = log_entry

            subject = f"New Log Record: {record.levelname}"
            send_email_async(subject, email_body, [get_email_setting("ADMIN_EMAIL")])

        except Exception:  # pylint: disable=W0718
            self.handleError(record)

    @staticmethod
    def render_template(
        log_entry: str,
        request: Optional[Any] = None,
        template_path: str = "email_notifier_template.html",
    ) -> str:
        """Renders the email body using a Jinja2 template.

        This method uses the provided log entry and request (if available)
        to generate an HTML email body. The email includes details such as the
        log message, current date and time, the IP address, and browser type
        of the user making the request.

        Args:
        ----
            log_entry (str): The formatted log message to be included in the email.
            request (Optional[Any]): The request associated with the log entry, if available.
            template_path (str): The path to the template to be used for rendering the email.
                                 Defaults to "email_notifier_template.html".

        Returns:
        -------
            str: The rendered email body as a string.

        """
        # Fetch IP address and user agent using the request helpers
        ip_address = get_ip_address(request) if request is not None else "Unknown"
        user_agent = get_user_agent(request) if request is not None else "Unknown"

        # Get current time
        current_time = datetime.now().astimezone()

        # Format date and time separately
        formatted_date = current_time.strftime("%d %B %Y").replace(
            current_time.strftime("%B"), current_time.strftime("%B").upper()
        )
        formatted_time = current_time.strftime("%I:%M %p")

        context = {
            "message": log_entry,
            "date": formatted_date,
            "time": formatted_time,
            "browser_type": user_agent,
            "ip_address": ip_address,
        }

        return render_to_string(template_path, context)
