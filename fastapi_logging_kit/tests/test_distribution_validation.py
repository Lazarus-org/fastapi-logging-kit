"""Release checks must reject divergent version metadata before publishing."""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import verify_distributions


@pytest.mark.parametrize(
    "runtime, commitizen, expected",
    [
        ("1.0.1", "1.0.0", "package __version__"),
        ("1.0.0", "1.0.1", "Commitizen version"),
    ],
)
def test_release_rejects_inconsistent_versions(
    tmp_path, monkeypatch, runtime, commitizen, expected
):
    package = tmp_path / "fastapi_logging_kit"
    package.mkdir()
    (package / "__init__.py").write_text(f'__version__ = "{runtime}"\n')
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "1.0.0"\n'
        f'[tool.commitizen]\nversion = "{commitizen}"\n'
    )
    monkeypatch.setattr(verify_distributions, "ROOT", tmp_path)

    with pytest.raises(SystemExit, match=expected):
        verify_distributions.load_project()


@pytest.mark.parametrize("tag", ["v9.9.9", "1.0.0"])
def test_release_rejects_wrong_tag_before_artifact_checks(tmp_path, tag):
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/verify_distributions.py"),
            str(tmp_path),
            "--tag",
            tag,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "release tag" in result.stderr
    expected = verify_distributions.load_project()["version"]
    assert f"must equal v{expected}" in result.stderr


def test_project_release_versions_agree():
    assert verify_distributions.load_project()["name"] == "fastapi-logging-kit"
