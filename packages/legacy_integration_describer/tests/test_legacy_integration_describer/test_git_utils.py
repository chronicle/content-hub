from __future__ import annotations

from typing import TYPE_CHECKING

from legacy_integration_describer.git_utils import find_integration_path

if TYPE_CHECKING:
    from pathlib import Path


def test_find_integration_path(tmp_path: Path) -> None:
    repo_dir = tmp_path / "tip-marketplace"
    integration_dir = repo_dir / "Integrations" / "TestIntegration"
    integration_dir.mkdir(parents=True)

    repos_config = [(repo_dir, "Integrations")]
    cwd, rel, full = find_integration_path("TestIntegration", repos_config)

    assert cwd == repo_dir
    assert rel == "Integrations/TestIntegration"
    assert full == integration_dir


def test_find_integration_path_missing(tmp_path: Path) -> None:
    repo_dir = tmp_path / "tip-marketplace"

    repos_config = [(repo_dir, "Integrations")]
    cwd, rel, full = find_integration_path("MissingIntegration", repos_config)

    assert cwd is None
    assert rel is None
    assert full is None
