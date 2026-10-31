"""Management command to archive and compress rotated log files."""

import gzip
import logging
import os
import re
import shutil
import tarfile
import tempfile
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi_logging_kit.commands.base import BaseCommand, build_runner

from fastapi_logging_kit.settings import settings_manager

logger = logging.getLogger(__name__)

# Supported directory bundle formats
BUNDLE_FORMATS = ("tar.gz", "zip")


class Command(BaseCommand):
    """Archive rotated log files into a timestamped subdirectory.

    By default this command:
    1. Scans the log directory for rotated files (anything that is NOT a
       plain ``<level>.log`` active log file, e.g. ``info.log.1``,
       ``debug.log.2024-01-15``, ``warning.log.1.gz``).
    2. Moves them into ``<LOG_DIR>/archive/<YYYY-MM-DD_HHMMSS>/``.
    3. Optionally compresses individual uncompressed files before moving
       (``--compress``).
    4. Optionally bundles the entire archive directory into a single
       ``tar.gz`` or ``zip`` file and removes the directory
       (``--bundle tar.gz`` or ``--bundle zip``).

    The active ``.log`` files are never touched.

    """

    help = (
        "Move rotated log files into a timestamped archive subdirectory, "
        "optionally compressing individual files (--compress) or bundling "
        "the whole archive into a single tar.gz / zip file (--bundle)."
    )

    def handle(self, *args: Tuple[Any], **kwargs: Any) -> None:
        """Archive the rotated log files.

        Args:
            *args: Positional arguments passed to the command.
            **kwargs: ``compress``, ``bundle`` and ``dry_run`` flags,
                supplied by the CLI or by a direct ``run()`` call.

        """
        log_dir: str = settings_manager.log_dir
        compress: bool = kwargs.get("compress", False)
        bundle: Optional[str] = kwargs.get("bundle")
        dry_run: bool = kwargs.get("dry_run", False)

        if not os.path.isdir(log_dir):
            self.stdout.write(self.style.ERROR(f"Log directory not found: {log_dir}"))
            return

        rotated_files = self._collect_rotated_files(log_dir)

        if not rotated_files:
            self.stdout.write(self.style.SUCCESS("No rotated log files found."))
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")
        archive_dir = os.path.join(log_dir, "archive", timestamp)
        bundle_path = f"{archive_dir}.{bundle}" if bundle else None

        if dry_run:
            self._print_dry_run(
                rotated_files, archive_dir, compress, bundle, bundle_path
            )
            return

        # --- Step 1: move (and optionally compress) individual files ---
        archived = self._move_files(rotated_files, archive_dir, compress)

        self.stdout.write(
            self.style.SUCCESS(
                f"Archived {len(archived)} file(s) to {archive_dir}:\n"
                + "\n".join(f"  {f}" for f in archived)
            )
        )
        logger.info(
            "Archived %d rotated log file(s) to %s.", len(archived), archive_dir
        )

        # --- Step 2: bundle the directory if requested ---
        if bundle:
            self._bundle_directory(archive_dir, bundle_path, bundle)

    # ------------------------------------------------------------------
    # File collection
    # ------------------------------------------------------------------

    def _collect_rotated_files(self, log_dir: str) -> List[str]:
        """Select only recognized rotated log files, excluding symlinks.

        Active log files, arbitrary files, and the archive tree are never
        moved. Relative directory structure is retained by ``_move_files``.
        """
        from fastapi_logging_kit.constants.default_settings import DefaultLoggingSettings

        levels = set(DefaultLoggingSettings().log_levels)
        configured = settings_manager.log_levels
        if isinstance(configured, (list, tuple)):
            levels.update(level for level in configured if isinstance(level, str))
        prefixes = "|".join(
            re.escape(level.lower()) for level in sorted(levels) if level
        )
        if not prefixes:
            return []

        rotated_name = re.compile(
            rf"^(?:{prefixes})\.(?:log|json|xml)\."
            rf"(?:[1-9][0-9]*|[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}"
            rf"(?:_[0-9]{{2}}(?:-[0-9]{{2}}(?:-[0-9]{{2}})?)?)?)"
            rf"(?:\.gz)?$"
        )
        rotated: List[str] = []
        for root, dirs, files in os.walk(log_dir, followlinks=False):
            dirs[:] = [
                name for name in dirs
                if name != "archive" and not os.path.islink(os.path.join(root, name))
            ]
            for filename in files:
                path = os.path.join(root, filename)
                if not os.path.islink(path) and rotated_name.fullmatch(filename):
                    rotated.append(path)
        return sorted(rotated)

    # ------------------------------------------------------------------
    # Move / compress individual files
    # ------------------------------------------------------------------

    def _move_files(
        self, rotated_files: List[str], archive_dir: str, compress: bool
    ) -> List[str]:
        """Archive rotated files atomically while retaining nested paths."""
        log_dir = os.path.abspath(settings_manager.log_dir)
        os.makedirs(archive_dir, exist_ok=False)
        archived: List[str] = []

        for source in rotated_files:
            source_path = os.path.abspath(source)
            relative = os.path.relpath(source_path, log_dir)
            if relative == os.pardir or relative.startswith(os.pardir + os.sep):
                raise ValueError("Rotated log path escapes LOG_DIR")

            destination = os.path.join(archive_dir, relative)
            if compress and not source_path.endswith(".gz"):
                destination += ".gz"
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            if os.path.lexists(destination):
                raise FileExistsError(destination)

            if compress and not source_path.endswith(".gz"):
                descriptor, temporary = tempfile.mkstemp(
                    prefix=".fastapi-logging-kit-", suffix=".tmp",
                    dir=os.path.dirname(destination),
                )
                try:
                    with os.fdopen(descriptor, "wb") as raw:
                        with gzip.GzipFile(fileobj=raw, mode="wb") as compressed:
                            with open(source_path, "rb") as original:
                                shutil.copyfileobj(original, compressed)
                    os.replace(temporary, destination)
                    os.remove(source_path)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            else:
                shutil.move(source_path, destination)
            archived.append(destination)

        return archived

    # ------------------------------------------------------------------
    # Directory bundling
    # ------------------------------------------------------------------

    def _bundle_directory(self, archive_dir: str, bundle_path: str, fmt: str) -> None:
        """Compress *archive_dir* into *bundle_path* and remove the directory.

        Args:
            archive_dir: The directory to bundle.
            bundle_path: Full destination path for the bundle file.
            fmt: One of ``"tar.gz"`` or ``"zip"``.

        """
        if fmt == "tar.gz":
            self._make_targz(archive_dir, bundle_path)
        elif fmt == "zip":
            self._make_zip(archive_dir, bundle_path)

        # Remove the now-bundled directory
        shutil.rmtree(archive_dir)

        size_mb = os.path.getsize(bundle_path) / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(
                f"Bundled archive directory into {bundle_path} "
                f"({size_mb:.2f} MB) and removed the source directory."
            )
        )
        logger.info(
            "Archive directory bundled into %s (%.2f MB).", bundle_path, size_mb
        )

    @staticmethod
    def _make_targz(source_dir: str, dest_path: str) -> None:
        """Create a gzip-compressed tar archive of *source_dir* at
        *dest_path*."""
        with tarfile.open(dest_path, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))

    @staticmethod
    def _make_zip(source_dir: str, dest_path: str) -> None:
        """Create a zip archive of *source_dir* at *dest_path*."""
        with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(source_dir):
                for fname in files:
                    full_path = os.path.join(root, fname)
                    arcname = os.path.relpath(
                        full_path, start=os.path.dirname(source_dir)
                    )
                    zf.write(full_path, arcname)

    # ------------------------------------------------------------------
    # Dry-run output
    # ------------------------------------------------------------------

    def _print_dry_run(
        self,
        rotated_files: List[str],
        archive_dir: str,
        compress: bool,
        bundle: Optional[str],
        bundle_path: Optional[str],
    ) -> None:
        self.stdout.write(
            self.style.WARNING(
                f"[DRY RUN] Would archive {len(rotated_files)} file(s) "
                f"to {archive_dir}:"
            )
        )
        for f in rotated_files:
            action = " (+ gzip)" if compress and not f.endswith(".gz") else ""
            self.stdout.write(f"  {f}{action}")

        if bundle:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would then bundle the directory into: {bundle_path}\n"
                    f"          and remove: {archive_dir}"
                )
            )


run = build_runner(Command)
