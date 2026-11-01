import sys
import tomllib
from importlib.metadata import requires
from pathlib import Path

import pytest
from packaging.requirements import Requirement

import fastapi_logging_kit
from fastapi_logging_kit.exceptions import FastLoggingError, ImproperlyConfigured
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestExceptions:
    """Test suite for the exception hierarchy of `fastapi_logging_kit`."""

    def test_improperly_configured_subclasses_the_base_error(self) -> None:
        """Test that ImproperlyConfigured derives from FastLoggingError."""
        assert issubclass(ImproperlyConfigured, FastLoggingError)
        assert issubclass(FastLoggingError, Exception)

    def test_improperly_configured_is_catchable_as_the_base_error(self) -> None:
        """Test that the base class catches the configuration error."""
        with pytest.raises(FastLoggingError, match="missing SMTP settings"):
            raise ImproperlyConfigured("missing SMTP settings")


class TestPublicApi:
    """Test suite for the names exported by the `fastapi_logging_kit` package."""

    @pytest.mark.parametrize("name", fastapi_logging_kit.__all__)
    def test_every_exported_name_is_importable(self, name: str) -> None:
        """Test that each name in ``__all__`` exists on the package.

        Args:
            name (str): The exported name under test.

        """
        assert hasattr(fastapi_logging_kit, name)

    def test_all_is_sorted_and_unique(self) -> None:
        """Test that ``__all__`` holds unique, sorted names."""
        assert fastapi_logging_kit.__all__ == sorted(set(fastapi_logging_kit.__all__))

    def test_version_is_a_string(self) -> None:
        """Test that the package exposes a non-empty version string."""
        assert isinstance(fastapi_logging_kit.__version__, str)
        assert fastapi_logging_kit.__version__

    def test_setup_logging_is_the_documented_entry_point(self) -> None:
        """Test that ``setup_logging`` is re-exported from the app module."""
        from fastapi_logging_kit.app import setup_logging

        assert fastapi_logging_kit.setup_logging is setup_logging

    def test_distribution_name_and_cli_entry_point_match_public_identity(self) -> None:
        """Test that distribution and CLI metadata use the selected package name."""
        project_root = Path(__file__).resolve().parents[2]
        metadata = tomllib.loads((project_root / "pyproject.toml").read_text())

        assert metadata["project"]["name"] == "fastapi-logging-kit"
        assert metadata["project"]["scripts"] == {
            "fastapi-logging-kit": "fastapi_logging_kit.commands.cli:main"
        }

    def test_package_version_matches_distribution_metadata(self) -> None:
        """Test that the runtime version matches the PEP 621 project version."""
        project_root = Path(__file__).resolve().parents[2]
        metadata = tomllib.loads((project_root / "pyproject.toml").read_text())

        assert fastapi_logging_kit.__version__ == metadata["project"]["version"]

    def test_package_declares_pep_561_typing_support(self) -> None:
        """Test that the PEP 561 marker ships with the source package."""
        package_root = Path(fastapi_logging_kit.__file__).resolve().parent

        assert (package_root / "py.typed").is_file()

    def test_installed_runtime_requirements_match_pep_621_metadata(self) -> None:
        """Check the built metadata against the authoritative project dependencies."""
        project_root = Path(__file__).resolve().parents[2]
        metadata = tomllib.loads((project_root / "pyproject.toml").read_text())
        expected = {Requirement(value) for value in metadata["project"]["dependencies"]}
        installed = {
            Requirement(value)
            for value in requires(metadata["project"]["name"]) or []
            if Requirement(value).marker is None
        }
        assert installed == expected

    def test_supported_python_range_matches_the_approved_matrix(self) -> None:
        """Test that metadata does not claim untested Python releases."""
        project_root = Path(__file__).resolve().parents[2]
        metadata = tomllib.loads((project_root / "pyproject.toml").read_text())
        classifiers = set(metadata["project"]["classifiers"])

        assert metadata["project"]["requires-python"] == ">=3.11,<3.16"
        assert {
            f"Programming Language :: Python :: 3.{minor}" for minor in range(11, 16)
        }.issubset(classifiers)
        assert "Programming Language :: Python :: 3.10" not in classifiers
