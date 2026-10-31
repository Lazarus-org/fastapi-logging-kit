import logging
import os
import threading
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP
from typing import List, Optional

from fastapi_logging_kit.utils.get_conf import get_email_setting

logger = logging.getLogger(__name__)


def _deliver(msg: MIMEMultipart, recipient_list: List[str]) -> None:
    """Connect to the configured SMTP server and deliver *msg*.

    Args:
        msg (MIMEMultipart): The message to send.
        recipient_list (List[str]): The addresses to deliver to.

    """
    server = SMTP(get_email_setting("EMAIL_HOST"), get_email_setting("EMAIL_PORT"))
    try:
        if get_email_setting("EMAIL_USE_TLS", True):
            server.starttls()
        server.login(
            get_email_setting("EMAIL_HOST_USER"),
            get_email_setting("EMAIL_HOST_PASSWORD"),
        )
        server.sendmail(
            get_email_setting("DEFAULT_FROM_EMAIL"), recipient_list, msg.as_string()
        )
    finally:
        server.quit()


def send_email_with_attachment(
    subject: str,
    body: str,
    recipient_list: List[str],
    attachment_path: str,
) -> None:
    """Send an email with a file attached, synchronously.

    This replaces Django's ``EmailMessage.attach_file`` + ``send``, used
    by the ``send-logs`` command to deliver the zipped log directory.

    Args:
        subject (str): The email subject line.
        body (str): The plain-text body of the email.
        recipient_list (List[str]): The addresses to deliver to.
        attachment_path (str): Path to the file to attach.

    Raises:
        Exception: Any error raised while connecting or sending.

    """
    msg = MIMEMultipart()
    msg["From"] = get_email_setting("DEFAULT_FROM_EMAIL")
    msg["To"] = ", ".join(recipient_list)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with open(attachment_path, "rb") as attachment:
        part = MIMEApplication(attachment.read())

    part.add_header(
        "Content-Disposition",
        "attachment",
        filename=os.path.basename(attachment_path),
    )
    msg.attach(part)

    _deliver(msg, recipient_list)


def send_email_async(
    subject: str,
    body: str,
    recipient_list: List[str],
    event: Optional[threading.Event] = None,
) -> None:
    """Send an HTML email in a background thread.

    The SMTP credentials are read from the ``EMAIL`` block of the
    ``fastapi_logging_kit`` configuration rather than from Django settings.

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
            _deliver(msg, recipient_list)
            logger.info("The Record has been sent to ADMIN EMAIL successfully.")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Email Notifier failed to send the Record: %s", e)

        finally:
            if event:
                event.set()  # set event that waits until email send. (used for Tests)

    # Start a new thread to send the email asynchronously
    email_thread = threading.Thread(target=send_email)
    email_thread.start()
