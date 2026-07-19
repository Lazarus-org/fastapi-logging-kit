import logging
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP
from typing import List, Optional

from fast_logging.utils.get_conf import get_email_setting

logger = logging.getLogger(__name__)


def send_email_async(
    subject: str,
    body: str,
    recipient_list: List[str],
    event: Optional[threading.Event] = None,
) -> None:
    """Send an HTML email in a background thread.

    The SMTP credentials are read from the ``EMAIL`` block of the
    ``fast_logging`` configuration rather than from Django settings.

    Args:
        subject (str): The email subject line.
        body (str): The HTML body of the email.
        recipient_list (List[str]): The addresses to deliver to.
        event (Optional[threading.Event]): Set once the send attempt
            finishes. Used by the tests to wait for the worker thread.

    """

    def send_email() -> None:
        from_email = get_email_setting("DEFAULT_FROM_EMAIL")

        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = ", ".join(recipient_list)
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "html"))

        try:
            server = SMTP(
                get_email_setting("EMAIL_HOST"), get_email_setting("EMAIL_PORT")
            )
            if get_email_setting("EMAIL_USE_TLS", True):
                server.starttls()
            server.login(
                get_email_setting("EMAIL_HOST_USER"),
                get_email_setting("EMAIL_HOST_PASSWORD"),
            )
            server.sendmail(from_email, recipient_list, msg.as_string())
            server.quit()
            logger.info("The Record has been sent to ADMIN EMAIL successfully.")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Email Notifier failed to send the Record: %s", e)

        finally:
            if event:
                event.set()  # set event that waits until email send. (used for Tests)

    # Start a new thread to send the email asynchronously
    email_thread = threading.Thread(target=send_email)
    email_thread.start()
