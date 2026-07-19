from typing import List

from fast_logging.checks import Error
from fast_logging.constants.required_email_settings import (
    EMAIL_REQUIRED_SETTINGS,
    NOTIFIER_EXTRA_REQUIRED_SETTING,
)
from fast_logging.settings import settings_manager


def check_email_settings(require_admin_email: bool = True) -> List[Error]:
    """Check if all required email settings are present in the configuration.

    Where ``django_logging`` looked these up as top-level Django
    settings, ``fast_logging`` reads them from the ``EMAIL`` block of its
    own configuration.

    Args:
        require_admin_email (bool): Whether ``ADMIN_EMAIL`` is also
            required, which is the case when a notification is being
            addressed to the administrator.

    Returns:
        List[Error]: An error for each missing required email setting.

    """
    errors: List[Error] = []

    # Build a fresh list rather than appending to the module-level constant,
    # which would accumulate duplicates across calls.
    required_settings = list(EMAIL_REQUIRED_SETTINGS)
    if require_admin_email:
        required_settings.append(NOTIFIER_EXTRA_REQUIRED_SETTING)

    email_settings = settings_manager.email_settings
    missed_settings = [
        setting for setting in required_settings if not email_settings.get(setting)
    ]

    if missed_settings:
        missing = ", ".join(missed_settings)
        errors.append(
            Error(
                f"Missing required email settings: {missing}",
                hint="Email settings required because you trying to send an email,"
                "Ensure all required email settings are properly configured in the "
                "EMAIL block of your fast_logging configuration.",
                id="fast_logging.E021",
            )
        )

    return errors
