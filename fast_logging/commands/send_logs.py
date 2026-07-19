import logging
import os
import shutil
import tempfile
from typing import Any, Dict, Tuple

from fast_logging.commands.base import BaseCommand, build_runner
from fast_logging.exceptions import ImproperlyConfigured
from fast_logging.settings import settings_manager
from fast_logging.utils.log_email_notifier.notifier import send_email_with_attachment
from fast_logging.validators.email_settings_validator import check_email_settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """A command that zips the log directory and sends it to the specified
    email address.

    This command is used to send the log files to a specified email
    address. It zips the log directory, creates an email with the zipped
    file as an attachment, and sends it to the specified email address.

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

        # Create a temporary file to store the zipped logs
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            zip_path = f"{tmp_file.name}.zip"
            tmp_file.close()

            # Zip the log directory
            shutil.make_archive(tmp_file.name, "zip", log_dir)

        # Send the email with the zipped logs
        email_subject = "Log Files"
        email_body = "Please find the attached log files."

        try:
            send_email_with_attachment(
                subject=email_subject,
                body=email_body,
                recipient_list=[email],
                attachment_path=zip_path,
            )
            self.stdout.write(self.style.SUCCESS(f"Logs sent successfully to {email}."))
            logger.info("Logs sent successfully to %s.", email)
        except Exception as e:  # pylint: disable=W0718
            self.stdout.write(self.style.ERROR(f"Failed to send logs: {e}"))
            logger.error("Failed to send logs: %s", e)
        finally:
            # Clean up the temporary file if exists
            if os.path.exists(zip_path):
                os.remove(zip_path)
                logger.info("Temporary zip file cleaned up successfully.")

    @staticmethod
    def validate_email_settings(require_admin_email: bool = False) -> None:
        """Check if all required email settings are present in the
        configuration.

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
