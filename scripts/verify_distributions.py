"""Verify wheel and source-distribution contents against project metadata."""

from __future__ import annotations

import argparse
import ast
import configparser
import email
import re
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    """Stop the release check with an actionable explanation."""
    raise SystemExit(f"Distribution verification failed: {message}")


def canonicalize_name(name: str) -> str:
    """Normalize a distribution name according to PyPI name rules."""
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    """Extract the distribution name from a PEP 508 requirement."""
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    if match is None:
        fail(f"cannot parse dependency name from {requirement!r}")
    return canonicalize_name(match.group(1))


def load_project() -> dict[str, Any]:
    """Read the canonical PEP 621 project metadata."""
    project_file = ROOT / "pyproject.toml"
    if not project_file.is_file():
        fail(f"project metadata file is missing: {project_file}")
    metadata = tomllib.loads(project_file.read_text(encoding="utf-8"))
    project = metadata["project"]
    module = ast.parse(
        (ROOT / "fastapi_logging_kit/__init__.py").read_text(encoding="utf-8")
    )
    versions = [
        ast.literal_eval(node.value)
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in node.targets
        )
    ]
    if versions != [project["version"]]:
        fail("package __version__ does not match pyproject.toml")
    if metadata["tool"]["commitizen"]["version"] != project["version"]:
        fail("Commitizen version does not match pyproject.toml")
    return project


def verify_wheel(path: Path, project: dict[str, Any]) -> None:
    """Validate wheel metadata and ensure runtime resources are packaged."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata_paths = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_paths) != 1:
            fail("wheel must contain exactly one dist-info/METADATA file")
        metadata = email.message_from_bytes(archive.read(metadata_paths[0]))

        expected_name = canonicalize_name(project["name"])
        actual_name = canonicalize_name(metadata.get("Name", ""))
        if actual_name != expected_name:
            fail(f"wheel name {actual_name!r} does not match {expected_name!r}")
        if metadata.get("Version") != project["version"]:
            fail("wheel version does not match pyproject.toml")
        if metadata.get("Requires-Python") != project["requires-python"]:
            fail("wheel Requires-Python metadata does not match pyproject.toml")

        expected_license = project.get("license")
        if (
            isinstance(expected_license, str)
            and metadata.get("License-Expression") != expected_license
        ):
            fail("wheel SPDX license expression does not match pyproject.toml")
        expected_license_files = project.get("license-files", [])
        actual_license_files = metadata.get_all("License-File", [])
        missing_license_files = set(expected_license_files) - set(actual_license_files)
        if missing_license_files:
            fail(f"wheel metadata omits license files: {sorted(missing_license_files)}")

        requirements = [
            value.lower() for value in metadata.get_all("Requires-Dist", [])
        ]
        for dependency in project.get("dependencies", []):
            expected_dependency = requirement_name(dependency)
            if not any(
                requirement_name(value) == expected_dependency for value in requirements
            ):
                fail(f"wheel is missing runtime dependency metadata for {dependency}")

        expected_extras = set(project.get("optional-dependencies", {}))
        actual_extras = {
            value.lower() for value in metadata.get_all("Provides-Extra", [])
        }
        if expected_extras != actual_extras:
            fail(
                "wheel extras do not match pyproject.toml: "
                f"expected {sorted(expected_extras)}, got {sorted(actual_extras)}"
            )
        for extra, extra_requirements in project.get(
            "optional-dependencies", {}
        ).items():
            for dependency in extra_requirements:
                expected_dependency = requirement_name(dependency)
                if not any(
                    requirement_name(value) == expected_dependency
                    and re.search(
                        rf"extra\s*==\s*['\"]{re.escape(extra)}['\"]",
                        value,
                        re.I,
                    )
                    for value in requirements
                ):
                    fail(
                        f"wheel is missing {dependency!r} for optional extra {extra!r}"
                    )

        package_root = ROOT / "fastapi_logging_kit"
        expected_package_files = {
            path.relative_to(ROOT).as_posix()
            for path in package_root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".pyo"}
            and "tests" not in path.relative_to(package_root).parts
        }
        missing_package_files = expected_package_files - names
        if missing_package_files:
            fail(
                "wheel is missing package source or runtime resources: "
                f"{sorted(missing_package_files)}"
            )
        if any(name.startswith("fastapi_logging_kit/tests/") for name in names):
            fail("wheel must not contain the internal test suite")
        if any(name.startswith("docs/") for name in names):
            fail("wheel must not contain the documentation source tree")
        if any(
            "__pycache__" in name or name.endswith((".pyc", ".pyo")) for name in names
        ):
            fail("wheel must not contain Python bytecode or cache directories")

        entry_points_paths = [
            name for name in names if name.endswith(".dist-info/entry_points.txt")
        ]
        if len(entry_points_paths) != 1:
            fail("wheel must contain exactly one entry_points.txt file")
        entry_points = configparser.ConfigParser()
        entry_points.read_string(archive.read(entry_points_paths[0]).decode("utf-8"))
        expected_entry_point = "fastapi_logging_kit.commands.cli:main"
        if (
            not entry_points.has_option("console_scripts", "fastapi-logging-kit")
            or entry_points.get("console_scripts", "fastapi-logging-kit")
            != expected_entry_point
        ):
            fail("wheel is missing the fastapi-logging-kit console entry point")


def verify_sdist(path: Path) -> None:
    """Ensure the source distribution contains the files needed to maintain it."""
    with tarfile.open(path, "r:gz") as archive:
        names = {member.name for member in archive.getmembers() if member.isfile()}
    if any(
        "/docs/_build/" in name
        or "__pycache__" in name
        or name.endswith((".pyc", ".pyo"))
        for name in names
    ):
        fail("sdist must not contain generated documentation or Python caches")

    required_suffixes = {
        "/AUTHORS.md",
        "/CODE_OF_CONDUCT.md",
        "/CONTRIBUTING.md",
        "/CONTRIBUTORS.md",
        "/SECURITY.md",
        "/CHANGELOG.md",
        "/LICENCE",
        "/README.md",
        "/pyproject.toml",
        "/tox.ini",
        "/docs/index.rst",
        "/docs/requirements.txt",
        "/docs/extensibility.rst",
        "/scripts/verify_distributions.py",
        "/packages/requirements.txt",
        "/packages/requirements-dev.txt",
        "/fastapi_logging_kit/tests/test_public_api.py",
        "/fastapi_logging_kit/tests/js/logiboard-security.test.mjs",
        "/fastapi_logging_kit/py.typed",
    }
    package_root = ROOT / "fastapi_logging_kit"
    required_suffixes.update(
        f"/{path.relative_to(ROOT).as_posix()}"
        for path in package_root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    )
    missing = {
        suffix
        for suffix in required_suffixes
        if not any(name.endswith(suffix) for name in names)
    }
    if missing:
        fail(f"sdist is missing source, tests or supporting files: {sorted(missing)}")


def main() -> None:
    """Verify exactly one wheel and one source distribution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", nargs="?", type=Path, default=Path("dist"))
    parser.add_argument("--tag", help="Release tag; must equal v<project version>")
    args = parser.parse_args()
    project = load_project()
    if args.tag is not None and args.tag != f"v{project['version']}":
        fail(f"release tag {args.tag!r} must equal v{project['version']}")
    dist = args.dist.resolve()
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        fail("expected exactly one wheel and one .tar.gz source distribution")
    verify_wheel(wheels[0], project)
    verify_sdist(sdists[0])
    print("Distribution contents and metadata verified.")


if __name__ == "__main__":
    main()
