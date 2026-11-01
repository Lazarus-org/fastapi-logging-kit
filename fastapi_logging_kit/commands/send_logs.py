import logging
import os
import shutil
import tempfile
from typing import Any, Dict, Tuple

from fastapi_logging_kit.commands.base import BaseCommand, build_runner
from fastapi_logging_kit.exceptions import ImproperlyConfigured
from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.utils.log_email_notifier.notifier import (
    send_email_with_attachment,
)
from fastapi_logging_kit.validators.email_settings_validator import check_email_settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """A command that zips the log directory and sends it to the specified email
    address.

    This command is used to send the log files to a specified email address. It zips the
    log directory, creates an email with the zipped file as an attachment, and sends it
    to the specified email address.
    """

    help = "Send log folder to the specified email address"

    def handle(self, *args: Tuple, **kwargs: Dict[str, Any]) -> None:
        """The main entry point for the command.

        Parameters:
            args (tuple): Positional arguments.
            kwargs (dict): Keyword arguments, containing the ``email`` to send to.
        """
        email: str = kwargs["email"]  # type: ignore[assignment]

        log_dir = settings_manager.log_dir

        if not os.path.exists(log_dir):
            self.stdout.write(
                self.style.ERROR(f'Log directory "{log_dir}" does not exist.')
            )
            logger.error("Log directory '%s' does not exist.", log_dir)
            return

        self.validate_email_settings()

        # Use a temporary directory so both the ZIP and its intermediate
        # archive base path are removed on success or failure.
        with tempfile.TemporaryDirectory(prefix="fastapi-logging-kit-") as temp_dir:
            archive_base = os.path.join(temp_dir, "logs")
            zip_path = shutil.make_archive(archive_base, "zip", log_dir)

            email_subject = "Log Files"
            email_body = "Please find the attached log files."

            try:
                send_email_with_attachment(
                    subject=email_subject,
                    body=email_body,
                    recipient_list=[email],
                    attachment_path=zip_path,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Logs sent successfully to {email}.")
                )
                logger.info("Logs sent successfully to %s.", email)
            except Exception as exc:  # pylint: disable=W0718
                self.stdout.write(self.style.ERROR(f"Failed to send logs: {exc}"))
                logger.error("Failed to send logs: %s", exc)

    @staticmethod
    def validate_email_settings(require_admin_email: bool = False) -> None:
        """Check if all required email settings are present in the configuration.

        Args:
            require_admin_email (bool): Whether ADMIN_EMAIL is also required.

        Raises:
            ImproperlyConfigured: If any of the required email settings
                are missing.
        """
        errors = check_email_settings(require_admin_email=require_admin_email)
        if errors:
            logger.error(errors)
            raise ImproperlyConfigured(errors)


run = build_runner(Command)
