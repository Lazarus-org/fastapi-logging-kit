import logging
import os
import threading
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP
from typing import List, Optional

from fastapi_logging_kit.utils.get_conf import get_email_setting
from fastapi_logging_kit.settings import settings_manager

logger = logging.getLogger(__name__)


_MAX_CONCURRENT_DEFAULT = 4
_TIMEOUT_DEFAULT = 10
_limiter_lock = threading.Lock()
_limiter_pid: int | None = None
_limiter_capacity: int | None = None
_limiter: threading.BoundedSemaphore | None = None


def _options() -> tuple[int, int]:
    """Load resource bounds independently of the external settings module."""
    values = settings_manager.email_notifier
    if not isinstance(values, dict):
        values = {}
    concurrent = values.get("MAX_CONCURRENT", _MAX_CONCURRENT_DEFAULT)
    timeout = values.get("SMTP_TIMEOUT", _TIMEOUT_DEFAULT)
    if type(concurrent) is not int or not 1 <= concurrent <= 64:
        raise ValueError("LOG_EMAIL_NOTIFIER.MAX_CONCURRENT must be an integer from 1 to 64")
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("LOG_EMAIL_NOTIFIER.SMTP_TIMEOUT must be an integer from 1 to 120")
    return concurrent, timeout


def _semaphore(capacity: int) -> threading.BoundedSemaphore:
    """Return a per-process capacity semaphore, reset when settings change."""
    global _limiter, _limiter_pid, _limiter_capacity
    with _limiter_lock:
        pid = os.getpid()
        if _limiter_pid != pid or _limiter is None or _limiter_capacity != capacity:
            _limiter = threading.BoundedSemaphore(capacity)
            _limiter_pid = pid
            _limiter_capacity = capacity
        return _limiter


def _after_fork() -> None:
    """Discard lock/semaphore inherited from a prefork server."""
    global _limiter_lock, _limiter, _limiter_pid, _limiter_capacity
    _limiter_lock = threading.Lock()
    _limiter = None
    _limiter_pid = os.getpid()
    _limiter_capacity = None


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork)


def _deliver(msg: MIMEMultipart, recipient_list: List[str]) -> None:
    """Connect to the configured SMTP server and deliver *msg*.

    Args:
        msg (MIMEMultipart): The message to send.
        recipient_list (List[str]): The addresses to deliver to.

    """
    server = SMTP(
        get_email_setting("EMAIL_HOST"),
        get_email_setting("EMAIL_PORT"),
        timeout=_options()[1],
    )
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
) -> bool:
    """Attempt best-effort delivery without spawning unbounded threads.

    Returns ``False`` when saturated. SMTP is never treated as a durable queue.
    """
    capacity, _timeout = _options()
    slot = _semaphore(capacity)
    if not slot.acquire(blocking=False):
        logger.warning("Email notifier at capacity; dropping notification")
        if event is not None:
            event.set()
        return False

    def send_email() -> None:
        try:
            from_email = get_email_setting("DEFAULT_FROM_EMAIL")
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = ", ".join(recipient_list)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))
            _deliver(msg, recipient_list)
            logger.info("The Record has been sent to ADMIN EMAIL successfully.")
        except Exception as exc:
            logger.warning("Email Notifier failed to send the Record: %s", exc)
        finally:
            slot.release()
            if event is not None:
                event.set()

    try:
        worker = threading.Thread(
            target=send_email,
            name="fastapi-logging-kit-email",
            daemon=True,
        )
        worker.start()
    except Exception:
        slot.release()
        if event is not None:
            event.set()
        raise
    return True
