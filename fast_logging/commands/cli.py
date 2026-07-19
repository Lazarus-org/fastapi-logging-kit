"""The ``fast-logging`` command line interface.

``django_logging`` exposed its commands through ``manage.py``. FastAPI
projects have no equivalent, so the same commands are published here as
a Typer application, installed as the ``fast-logging`` console script::

    fast-logging send-logs ops@example.com
    fast-logging archive-logs --compress --bundle tar.gz
    fast-logging logs-size-audit
    fast-logging rotate-logs
    fast-logging generate-pretty-json
    fast-logging generate-pretty-xml

Each command reads the same configuration the application does, so
``FAST_LOGGING_``-prefixed environment variables (notably
``FAST_LOGGING_LOG_DIR``) apply to the CLI too.

"""

from typing import Optional

import typer

from fast_logging.commands import archive_logs as archive_logs_command
from fast_logging.commands import generate_pretty_json as generate_pretty_json_command
from fast_logging.commands import generate_pretty_xml as generate_pretty_xml_command
from fast_logging.commands import logs_size_audit as logs_size_audit_command
from fast_logging.commands import rotate_logs as rotate_logs_command
from fast_logging.commands import send_logs as send_logs_command
from fast_logging.commands.archive_logs import BUNDLE_FORMATS

app = typer.Typer(
    name="fast-logging",
    help="Maintenance commands for the fast_logging package.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command("send-logs")
def send_logs(
    email: str = typer.Argument(..., help="The email address to send the logs to"),
) -> None:
    """Zip the log directory and send it to the specified email address."""
    send_logs_command.run(email=email)


@app.command("archive-logs")
def archive_logs(
    compress: bool = typer.Option(
        False,
        "--compress",
        help="Gzip-compress each uncompressed rotated file before archiving.",
    ),
    bundle: Optional[str] = typer.Option(
        None,
        "--bundle",
        metavar="FORMAT",
        help=(
            "After archiving, bundle the entire archive directory into a "
            "single compressed file and remove the directory. "
            f"Supported formats: {', '.join(BUNDLE_FORMATS)}."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print what would happen without touching any files.",
    ),
) -> None:
    """Move rotated log files into a timestamped archive subdirectory."""
    if bundle is not None and bundle not in BUNDLE_FORMATS:
        raise typer.BadParameter(
            f"'{bundle}' is not a supported bundle format. "
            f"Choose from: {', '.join(BUNDLE_FORMATS)}."
        )

    archive_logs_command.run(compress=compress, bundle=bundle, dry_run=dry_run)


@app.command("logs-size-audit")
def logs_size_audit() -> None:
    """Check the log directory size and warn the admin if it is too large."""
    logs_size_audit_command.run()


@app.command("rotate-logs")
def rotate_logs() -> None:
    """Trigger an immediate rotation of all rotating log handlers."""
    rotate_logs_command.run()


@app.command("generate-pretty-json")
def generate_pretty_json() -> None:
    """Reformat the JSON log files into valid, pretty-printed JSON arrays."""
    generate_pretty_json_command.run()


@app.command("generate-pretty-xml")
def generate_pretty_xml() -> None:
    """Reformat the XML log files by wrapping them in a <logs> element."""
    generate_pretty_xml_command.run()


def main() -> None:
    """Entry point for the ``fast-logging`` console script."""
    app()


if __name__ == "__main__":
    main()
