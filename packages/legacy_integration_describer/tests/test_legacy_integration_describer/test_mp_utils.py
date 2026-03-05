from __future__ import annotations

from typing import TYPE_CHECKING

from legacy_integration_describer.mp_utils import parse_ai_metadata

if TYPE_CHECKING:
    from pathlib import Path


def test_parse_ai_metadata(tmp_path: Path) -> None:
    integration_dir = tmp_path / "TestIntegration"
    integration_dir.mkdir()

    yaml_content = """
MyAction:
  description: "Runs a test action"
  categories: ["Investigate", "Enrich"]
  entity_usage:
    - User
    - IP
"""
    yaml_file = integration_dir / "actions_ai_description.yaml"
    yaml_file.write_text(yaml_content)

    errors = []
    results = parse_ai_metadata(integration_dir, errors)

    assert len(errors) == 0
    assert len(results) == 1

    result = results[0]
    assert result.integration_name == "TestIntegration"
    assert result.action_name == "MyAction"
    assert result.description == "Runs a test action"
    assert "Investigate" in result.categories
    assert "User" in result.entity_usage
