# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import pathlib
import sqlite3

import pytest
from typer.testing import CliRunner

import mp.describe.evaluate.rules
from mp.describe.evaluate.evaluator import (
    EvaluationEngine,
    get_code_for_action,
    load_integration_artifacts,
    normalize_action_name,
)
from mp.describe.evaluate.models import (
    EvaluationReport,
    RuleEvaluationResult,
    VerdictEnum,
)
from mp.describe.evaluate.reporter import EvaluationReporter
from mp.describe.evaluate.rules import (
    EVALUATION_RULES,
    EvaluationRule,
    build_evaluation_prompt,
)
from mp.describe.evaluate.storage import EvaluationStorage
from mp.describe.typer_app import app

runner = CliRunner()
DEFAULT_RULESET_PATH = pathlib.Path(mp.describe.evaluate.rules.__file__).parent / "default_rules.yaml"


def test_models_serialization() -> None:
    """Test serializing EvaluationReport model to dict."""
    res = RuleEvaluationResult(
        evaluation_id="eval_1",
        integration_id="ActiveDirectory",
        action_id="create_user",
        run_id="run_1",
        evaluated_at="2026-07-29T12:00:00Z",
        rule_title="ai_description Field Structure",
        verdict=VerdictEnum.PASS,
        reasoning="All sub-sections exist.",
    )

    report = EvaluationReport(
        integration_id="ActiveDirectory",
        run_id="run_1",
        evaluated_at="2026-07-29T12:00:00Z",
        total_evaluations=1,
        pass_count=1,
        fail_count=0,
        partial_count=0,
        score_percentage=100.0,
        results=[res],
    )

    data = report.to_dict()
    assert data["integration_id"] == "ActiveDirectory"
    assert data["score_percentage"] == 100.0
    assert len(data["results"]) == 1
    assert data["results"][0]["verdict"] == "PASS"


def test_storage_save_and_retrieve(tmp_path: pathlib.Path) -> None:
    """Test saving and retrieving evaluation results using SQLite."""
    db_file = tmp_path / "test_eval.db"
    storage = EvaluationStorage(db_file)

    res = RuleEvaluationResult(
        evaluation_id="eval_001",
        integration_id="Okta",
        action_id="all_actions",
        run_id="run_test",
        evaluated_at="2026-07-29T12:00:00Z",
        rule_title="ai_short_description Style",
        verdict=VerdictEnum.PASS,
        reasoning="Concise and starts with an active verb.",
        suggested_fix=None,
    )

    storage.save_evaluation(res)

    records = storage.get_evaluations(integration_id="Okta", run_id="run_test")
    assert len(records) == 1
    assert records[0].evaluation_id == "eval_001"
    assert records[0].verdict == VerdictEnum.PASS


def test_storage_save_and_retrieve_rules(tmp_path: pathlib.Path) -> None:
    """Test saving and retrieving rules in EvaluationStorage."""
    db_file = tmp_path / "test_rules.db"
    storage = EvaluationStorage(db_file)

    rule1 = EvaluationRule(
        title="Custom Rule 1",
        target_field="ai_description",
        criteria="Check description accuracy",
        rule_id="rule_custom_1",
    )
    rule2 = EvaluationRule(
        title="Custom Rule 2",
        target_field="parameters_description",
        criteria="Check table headers",
        rule_id="rule_custom_2",
    )

    storage.save_rules([rule1, rule2])
    saved_rules = storage.get_rules()

    assert len(saved_rules) == 2
    rule_ids = {r.rule_id for r in saved_rules}
    assert "rule_custom_1" in rule_ids
    assert "rule_custom_2" in rule_ids


def test_engine_saves_rules_and_links_rule_id(tmp_path: pathlib.Path) -> None:
    """Test that EvaluationEngine persists rules to SQLite DB and populates rule_id in results."""
    db_file = tmp_path / "engine_eval.db"
    (tmp_path / "mock_integration").mkdir()

    engine = EvaluationEngine()
    report = engine.evaluate_integration(
        integration_id="mock_integration",
        src=tmp_path,
        db_path=db_file,
        use_llm=False,
    )

    assert report.total_evaluations > 0
    for res in report.results:
        assert res.rule_id != "", f"Result for rule '{res.rule_title}' must have a non-empty rule_id"

    storage = EvaluationStorage(db_file)
    db_rules = storage.get_rules()
    assert len(db_rules) == len(mp.describe.evaluate.rules.EVALUATION_RULES)

    # Verify SQL join between rule_evaluations and rules table
    with storage._get_connection() as conn:  # ruff:ignore[private-member-access]
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT e.evaluation_id, e.rule_id, r.title, r.target_field
            FROM rule_evaluations e
            JOIN rules r ON e.rule_id = r.rule_id
            """
        )
        joined_rows = cursor.fetchall()
        assert len(joined_rows) == len(report.results)


def test_reporter_export(tmp_path: pathlib.Path) -> None:
    """Test EvaluationReporter exporting Markdown, JSON, and HTML."""
    res = RuleEvaluationResult(
        evaluation_id="eval_1",
        integration_id="ActiveDirectory",
        action_id="all_actions",
        run_id="run_1",
        evaluated_at="2026-07-29T12:00:00Z",
        rule_title="ai_description Field Structure",
        verdict=VerdictEnum.PASS,
        reasoning="All sub-sections exist.",
    )

    report = EvaluationReport(
        integration_id="ActiveDirectory",
        run_id="run_1",
        evaluated_at="2026-07-29T12:00:00Z",
        total_evaluations=1,
        pass_count=1,
        fail_count=0,
        partial_count=0,
        score_percentage=100.0,
        results=[res],
    )

    md_out = tmp_path / "report.md"
    json_out = tmp_path / "report.json"
    html_out = tmp_path / "report.html"

    EvaluationReporter.export_report(report, "markdown", md_out)
    EvaluationReporter.export_report(report, "json", json_out)
    EvaluationReporter.export_report(report, "html", html_out)

    assert md_out.exists()
    assert "# Evaluation Report: `ActiveDirectory`" in md_out.read_text(encoding="utf-8")

    assert json_out.exists()
    assert '"integration_id": "ActiveDirectory"' in json_out.read_text(encoding="utf-8")

    assert html_out.exists()
    assert "<title>Evaluation Report - ActiveDirectory</title>" in html_out.read_text(encoding="utf-8")


def test_cli_help() -> None:
    """Test mp describe evaluate CLI help menu."""
    result = runner.invoke(app, ["evaluate", "--help"])
    assert result.exit_code == 0
    assert "Evaluate the logical quality of generated AI descriptions" in result.output


def test_cli_execution_invalid_integration() -> None:
    """Test mp describe evaluate CLI validation failure on missing integration."""
    result = runner.invoke(
        app,
        ["evaluate", "InvalidIntegrationName", "--ruleset", str(DEFAULT_RULESET_PATH)],
    )
    assert result.exit_code == 1


def test_cli_defaults_to_bundled_ruleset(tmp_path: pathlib.Path) -> None:
    """Test that mp describe evaluate CLI defaults to bundled ruleset when --ruleset is omitted."""
    integration_dir = tmp_path / "mock_integration"
    integration_dir.mkdir(exist_ok=True)
    result = runner.invoke(app, ["evaluate", "mock_integration", "--src", str(tmp_path)])
    assert result.exit_code == 0
    assert "Evaluation report saved to:" in result.output


def test_cli_evaluate_with_src_directly_to_integration_folder(tmp_path: pathlib.Path) -> None:
    """Test mp describe evaluate when --src points directly to an integration folder without positional arg."""
    integration_dir = tmp_path / "mock_integration"
    integration_dir.mkdir(exist_ok=True)
    (integration_dir / "pyproject.toml").write_text("[project]\nname = 'Mock Integration'\n", encoding="utf-8")
    result = runner.invoke(app, ["evaluate", "--src", str(integration_dir)])
    assert result.exit_code == 0
    assert "Evaluation report saved to:" in result.output


def test_cli_evaluate_with_integration_name_and_direct_src_folder(tmp_path: pathlib.Path) -> None:
    """Test mp describe evaluate when positional integration is given and --src points directly to that folder."""
    integration_dir = tmp_path / "mock_integration"
    integration_dir.mkdir(exist_ok=True)
    (integration_dir / "pyproject.toml").write_text("[project]\nname = 'Mock Integration'\n", encoding="utf-8")
    result = runner.invoke(app, ["evaluate", "mock_integration", "--src", str(integration_dir)])
    assert result.exit_code == 0
    assert "Evaluation report saved to:" in result.output


def test_load_rules_from_yaml_custom(tmp_path: pathlib.Path) -> None:
    """Test loading a custom ruleset YAML file."""
    custom_rules_file = tmp_path / "custom_rules.yaml"
    custom_rules_file.write_text(
        "- title: 'Custom Test Rule'\n  target_field: 'ai_description'\n  criteria: 'Custom check criteria'\n",
        encoding="utf-8",
    )
    rules = mp.describe.evaluate.rules.load_rules_from_yaml(custom_rules_file)
    assert len(rules) == 1
    assert rules[0].title == "Custom Test Rule"


def test_per_action_evaluation() -> None:
    """Test per-action Markdown rendering in EvaluationReporter."""
    res_1 = RuleEvaluationResult(
        evaluation_id="eval_act1",
        integration_id="virus_total",
        action_id="Get Domain Report",
        run_id="run_vt",
        evaluated_at="2026-07-30T10:00:00Z",
        rule_title="ai_description Field Structure",
        verdict=VerdictEnum.PASS,
        reasoning="Passed.",
    )
    res_2 = RuleEvaluationResult(
        evaluation_id="eval_act2",
        integration_id="virus_total",
        action_id="Ping",
        run_id="run_vt",
        evaluated_at="2026-07-30T10:00:00Z",
        rule_title="ai_description Field Structure",
        verdict=VerdictEnum.FAIL,
        reasoning="Failed.",
    )

    report = EvaluationReport(
        integration_id="virus_total",
        run_id="run_vt",
        evaluated_at="2026-07-30T10:00:00Z",
        total_evaluations=2,
        pass_count=1,
        fail_count=1,
        partial_count=0,
        score_percentage=50.0,
        results=[res_1, res_2],
    )

    rendered_md = EvaluationReporter.render_markdown(report)
    assert "## Action: `Get Domain Report`" in rendered_md
    assert "## Action: `Ping`" in rendered_md
    assert "🟢 PASS" in rendered_md
    assert "🔴 FAIL" in rendered_md


def test_evaluate_with_config_yaml_override(tmp_path: pathlib.Path) -> None:
    """Test evaluate_integration overriding default YAML with config_yaml parameter."""
    integration_dir = tmp_path / "mock_integration"
    integration_dir.mkdir()

    custom_yaml = tmp_path / "custom_actions.yaml"
    custom_yaml.write_text(
        """
TestCustomAction:
  ai_description: "Execute custom action. General Description \\n Flow Description \\n Additional Notes"
  ai_short_description: "Execute custom action."
  parameters_description: "| Parameter | Type | Mandatory | Description |"
""",
        encoding="utf-8",
    )

    engine = EvaluationEngine()
    report = engine.evaluate_integration(
        integration_id="mock_integration",
        src=tmp_path,
        config_yaml=custom_yaml,
        use_llm=False,
    )
    assert any(res.action_id == "TestCustomAction" for res in report.results)


def test_heuristic_evaluation_rules() -> None:
    """Test structural heuristic evaluation for rules."""
    verdict_1_pass, _, _ = EvaluationEngine.heuristic_evaluate_rule(
        "ai_description Field Structure",
        "ai_description",
        "General Description \\n Flow Description \\n Additional Notes",
    )
    assert verdict_1_pass == VerdictEnum.PASS

    verdict_1_fail, _, _ = EvaluationEngine.heuristic_evaluate_rule(
        "ai_description Field Structure", "ai_description", "Missing sections"
    )
    assert verdict_1_fail == VerdictEnum.FAIL

    verdict_3_pass, _, _ = EvaluationEngine.heuristic_evaluate_rule(
        "Parameters Table Header Formatting", "parameters_description", "There are no parameters for this action"
    )
    assert verdict_3_pass == VerdictEnum.PASS

    verdict_3_fail, _, _ = EvaluationEngine.heuristic_evaluate_rule(
        "Parameters Table Header Formatting", "parameters_description", "Some weird text"
    )
    assert verdict_3_fail == VerdictEnum.FAIL


def test_reporter_html_escaping() -> None:
    """Test HTML escaping in EvaluationReporter to prevent XSS and broken markup."""
    res = RuleEvaluationResult(
        evaluation_id="eval_xss",
        integration_id="<script>alert(1)</script>",
        action_id="<img src=x onerror=alert(1)>",
        run_id="run_xss",
        evaluated_at="2026-07-29T12:00:00Z",
        rule_title="<title_tag>",
        actual_value="<actual_val>",
        verdict=VerdictEnum.FAIL,
        reasoning="<reasoning_val>",
        suggested_fix="<fix_val>",
    )
    report = EvaluationReport(
        integration_id="<script>alert(1)</script>",
        run_id="run_xss",
        evaluated_at="2026-07-29T12:00:00Z",
        total_evaluations=1,
        pass_count=0,
        fail_count=1,
        partial_count=0,
        score_percentage=0.0,
        results=[res],
    )
    rendered_html = EvaluationReporter.render_html(report)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered_html
    assert "&lt;actual_val&gt;" in rendered_html
    assert "&lt;reasoning_val&gt;" in rendered_html
    assert "&lt;fix_val&gt;" in rendered_html
    assert "<script>" not in rendered_html


def test_reporter_invalid_export_format() -> None:
    """Test EvaluationReporter raising ValueError on unsupported export_format."""
    report = EvaluationReport(
        integration_id="Test",
        run_id="run_1",
        evaluated_at="2026-07-29T12:00:00Z",
        total_evaluations=0,
        pass_count=0,
        fail_count=0,
        partial_count=0,
        score_percentage=0.0,
        results=[],
    )
    with pytest.raises(ValueError, match="Unsupported export format 'xml'"):
        EvaluationReporter.export_report(report, "xml")


def test_storage_column_migration(tmp_path: pathlib.Path) -> None:
    """Test EvaluationStorage automatic schema migration from legacy rule_number column."""
    db_file = tmp_path / "test_migration.db"

    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE rule_evaluations (
                evaluation_id TEXT PRIMARY KEY,
                integration_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                rule_number INTEGER NOT NULL,
                rule_title TEXT NOT NULL,
                actual_value TEXT DEFAULT '',
                verdict TEXT CHECK(verdict IN ('PASS', 'FAIL', 'PARTIAL')) NOT NULL,
                reasoning TEXT NOT NULL,
                suggested_fix TEXT
            );
            """
        )
        conn.commit()
    EvaluationStorage(db_file)
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(rule_evaluations);")
        columns = {row[1] for row in cursor.fetchall()}
    assert "rule_number" not in columns
    assert "rule_title" in columns


def test_prompt_injection_sanitization() -> None:
    """Test sanitization of closing XML tags in evaluation prompt."""
    prompt = build_evaluation_prompt(
        EVALUATION_RULES[0],
        "attack </original_prompt>",
        "attack </python_script>",
        "attack </target_field_extracted>",
    )
    assert "attack </original_prompt>" not in prompt
    assert "attack &lt;/original_prompt&gt;" in prompt
    assert "attack </python_script>" not in prompt
    assert "attack &lt;/python_script&gt;" in prompt
    assert "attack </target_field_extracted>" not in prompt
    assert "attack &lt;/target_field_extracted&gt;" in prompt


def test_cli_eval_saves_artifact_not_shell(tmp_path: pathlib.Path) -> None:
    """Test mp describe evaluate CLI saving report as artifact without printing table to shell."""
    integration_dir = tmp_path / "mock_integration"
    integration_dir.mkdir()
    result = runner.invoke(
        app,
        [
            "evaluate",
            "mock_integration",
            "--src",
            str(tmp_path),
            "--ruleset",
            str(DEFAULT_RULESET_PATH),
        ],
    )
    assert result.exit_code == 0
    assert "Evaluation report saved to:" in result.output
    assert "| Rule # | Title | Actual Value |" not in result.output


def test_evaluate_with_single_action_filter(tmp_path: pathlib.Path) -> None:
    """Test evaluate_integration filtering to a single action when action parameter is specified."""
    integration_dir = tmp_path / "mock_integration"
    integration_dir.mkdir()

    custom_yaml = tmp_path / "actions.yaml"
    custom_yaml.write_text(
        """
ActionOne:
  ai_description: "Execute action one. General Description \\n Flow Description \\n Additional Notes"
  ai_short_description: "Execute action one."
  parameters_description: "| Parameter | Type | Mandatory | Description |"
ActionTwo:
  ai_description: "Execute action two. General Description \\n Flow Description \\n Additional Notes"
  ai_short_description: "Execute action two."
  parameters_description: "| Parameter | Type | Mandatory | Description |"
Upload And Scan Files:
  ai_description: "Upload and scan. General Description \\n Flow Description \\n Additional Notes"
  ai_short_description: "Upload and scan files."
  parameters_description: "| Parameter | Type | Mandatory | Description |"
""",
        encoding="utf-8",
    )

    engine = EvaluationEngine()
    report = engine.evaluate_integration(
        integration_id="mock_integration",
        src=tmp_path,
        config_yaml=custom_yaml,
        action="UploadAndScanFile",
        use_llm=False,
    )
    assert any(res.action_id == "Upload And Scan Files" for res in report.results)
    assert not any(res.action_id == "ActionOne" for res in report.results)
    assert not any(res.action_id == "ActionTwo" for res in report.results)


def test_reporter_add_prompt_html_button() -> None:
    """Test HTML report including collapsible button and prompt text when prompt is present."""
    res = RuleEvaluationResult(
        evaluation_id="eval_prompt",
        integration_id="TestInt",
        action_id="TestAction",
        run_id="run_1",
        evaluated_at="2026-07-29T12:00:00Z",
        rule_title="Rule 1",
        actual_value="val",
        verdict=VerdictEnum.PASS,
        reasoning="good",
        suggested_fix=None,
        prompt="<original_prompt>test prompt</original_prompt>",
    )
    report = EvaluationReport(
        integration_id="TestInt",
        run_id="run_1",
        evaluated_at="2026-07-29T12:00:00Z",
        total_evaluations=1,
        pass_count=1,
        fail_count=0,
        partial_count=0,
        score_percentage=100.0,
        results=[res],
    )
    rendered_html = EvaluationReporter.render_html(report)
    assert "<th>Prompt</th>" in rendered_html
    assert "Show/Hide Prompt" in rendered_html
    assert "&lt;original_prompt&gt;test prompt&lt;/original_prompt&gt;" in rendered_html
    assert 'class="modal"' in rendered_html
    assert "class='modal-content'" in rendered_html


def test_missing_yaml_keys_fail_rules_2_and_3(tmp_path: pathlib.Path) -> None:
    """Test that missing ai_short_description and parameters_description keys fail Rules #2 and #3."""
    (tmp_path / "mock_integration").mkdir()
    custom_yaml = tmp_path / "actions.yaml"
    custom_yaml.write_text(
        """
TestAction:
  ai_description: "General Description \\n Flow Description \\n Additional Notes"
""",
        encoding="utf-8",
    )

    engine = EvaluationEngine()
    report = engine.evaluate_integration(
        integration_id="mock_integration",
        src=tmp_path,
        config_yaml=custom_yaml,
        use_llm=False,
    )
    r2 = next(r for r in report.results if r.rule_title == "ai_short_description Structure & Scope Constraint")
    r3 = next(r for r in report.results if r.rule_title == "Parameters Table Header Formatting")
    assert r2.verdict == VerdictEnum.FAIL

    assert "target field 'ai_short_description' is missing" in r2.reasoning
    assert r3.verdict == VerdictEnum.FAIL
    assert "target field 'parameters_description' is missing" in r3.reasoning


def test_per_rule_yaml_field_validation(tmp_path: pathlib.Path) -> None:
    """Test per-rule YAML field validations for both missing and valid configurations."""
    (tmp_path / "mock_integration").mkdir()
    custom_yaml = tmp_path / "actions.yaml"
    custom_yaml.write_text(
        """
InvalidAction:
  ai_description: "General description text."
  ai_short_description: ""
ValidAction:
  ai_description: "### General Description \\n Test \\n ### Flow Description \\n Test \\n ### Additional Notes \\n None"
  ai_short_description: "Valid short description."
  parameters_description: "There are no parameters for this action"
  capabilities:
    can_mutate_external_data: false
    can_mutate_internal_data: false
    fetches_data: false
    reasoning: "No mutation"
  entity_usage:
    entity_types:
      address: false
  outcome_categories:
    SUCCESS: "No category"
""",
        encoding="utf-8",
    )

    engine = EvaluationEngine()
    report = engine.evaluate_integration(
        integration_id="mock_integration",
        src=tmp_path,
        config_yaml=custom_yaml,
        use_llm=False,
    )
    rule_t = "ai_short_description Structure & Scope Constraint"
    invalid_r2 = next(r for r in report.results if r.action_id == "InvalidAction" and r.rule_title == rule_t)
    valid_r2 = next(r for r in report.results if r.action_id == "ValidAction" and r.rule_title == rule_t)

    assert invalid_r2.verdict == VerdictEnum.FAIL
    assert "target field 'ai_short_description' is missing" in invalid_r2.reasoning
    assert valid_r2.verdict == VerdictEnum.PASS


def test_empty_yaml_file_generates_failure_report(tmp_path: pathlib.Path) -> None:
    """Test that an empty YAML file generates a complete failure report instead of zero results."""
    (tmp_path / "mock_integration").mkdir()
    empty_yaml = tmp_path / "empty_actions.yaml"
    empty_yaml.write_text("# Only comments\n", encoding="utf-8")

    engine = EvaluationEngine()
    report = engine.evaluate_integration(
        integration_id="mock_integration",
        src=tmp_path,
        config_yaml=empty_yaml,
        use_llm=False,
    )
    assert report.total_evaluations == len(mp.describe.evaluate.rules.EVALUATION_RULES)
    assert any(r.action_id == "Integration Actions (Missing or Empty YAML)" for r in report.results)
    for r in report.results:
        assert r.verdict == VerdictEnum.FAIL
        assert "target field" in r.reasoning


def test_yaml_null_values_handled_cleanly(tmp_path: pathlib.Path) -> None:
    """Test that explicit null values in YAML do not stringify to 'None' or 'null'."""
    (tmp_path / "mock_integration").mkdir()
    custom_yaml = tmp_path / "actions.yaml"
    custom_yaml.write_text(
        """
NullAction:
  ai_description: null
  ai_short_description: null
  parameters_description: null
  capabilities: null
  entity_usage: null
  outcome_categories: null
""",
        encoding="utf-8",
    )

    engine = EvaluationEngine()
    report = engine.evaluate_integration(
        integration_id="mock_integration",
        src=tmp_path,
        config_yaml=custom_yaml,
        use_llm=False,
    )
    for r in report.results:
        assert r.verdict == VerdictEnum.FAIL
        assert "target field" in r.reasoning
        assert "None" not in r.actual_value


def test_actiondef_files_included_in_action_code(tmp_path: pathlib.Path) -> None:
    """Test that both Python scripts and action definition files (.yaml/.json/.actiondef) are included."""
    integration_dir = tmp_path / "mock_integration"
    actions_dir = integration_dir / "actions"
    actions_dir.mkdir(parents=True)

    py_file = actions_dir / "EnrichEntities.py"
    py_file.write_text("def run(): pass\n", encoding="utf-8")

    yaml_def = actions_dir / "EnrichEntities.yaml"
    yaml_def.write_text("name: Enrich entities\nparameters: []\n", encoding="utf-8")

    source_files, _, _ = load_integration_artifacts("mock_integration", src=tmp_path)
    assert len(source_files) == 2
    combined_code, action_files, shared_files = get_code_for_action("EnrichEntities", source_files)
    assert len(action_files) == 2
    assert len(shared_files) == 0
    assert "actions/EnrichEntities.py" in action_files
    assert "actions/EnrichEntities.yaml" in action_files
    assert "# File: actions/EnrichEntities.py" in combined_code
    assert "# File: actions/EnrichEntities.yaml" in combined_code
    assert "name: Enrich entities" in combined_code


def test_action_name_matching_with_file_extension(tmp_path: pathlib.Path) -> None:
    assert normalize_action_name("UploadAndScanFile.py") == "uploadandscanfile"
    assert normalize_action_name("actions/UploadAndScanFile.py") == "uploadandscanfile"
    assert normalize_action_name("Upload And Scan Files:") == "uploadandscanfile"

    integration_dir = tmp_path / "mock_vt"
    actions_dir = integration_dir / "actions"
    actions_dir.mkdir(parents=True)
    (actions_dir / "UploadAndScanFile.py").write_text("def upload_and_scan_file(): pass\n", encoding="utf-8")

    ai_dir = integration_dir / "resources" / "ai"
    ai_dir.mkdir(parents=True)
    ai_yaml = ai_dir / "actions_ai_description.yaml"
    ai_yaml.write_text(
        "Upload And Scan Files:\n"
        "  ai_description: 'Upload and scan file.'\n"
        "  ai_short_description: 'Upload and scan file.'\n"
        "  parameters_description: 'There are no parameters for this action'\n"
        "  capabilities:\n"
        "    can_mutate: false\n"
        "    can_enrich: true\n",
        encoding="utf-8",
    )

    engine = EvaluationEngine()
    report = engine.evaluate_integration(
        integration_id="mock_vt",
        src=tmp_path,
        action="UploadAndScanFile.py",
        use_llm=False,
    )

    assert len(report.results) == len(mp.describe.evaluate.rules.EVALUATION_RULES)
    assert all(r.action_id == "Upload And Scan Files" for r in report.results)
    t2 = "ai_short_description Structure & Scope Constraint"
    t3 = "Parameters Table Header Formatting"
    res_rule_2 = next(r for r in report.results if r.rule_title == t2)

    res_rule_3 = next(r for r in report.results if r.rule_title == t3)
    assert res_rule_2.verdict == "PASS"
    assert res_rule_3.verdict == "PASS"


def test_integration_metadata_keys_ignored_in_evaluation(tmp_path: pathlib.Path) -> None:
    """Test that integration metadata keys like product_categories are never evaluated as actions."""
    integration_dir = tmp_path / "mock_meta"
    ai_dir = integration_dir / "resources" / "ai"
    ai_dir.mkdir(parents=True)
    (ai_dir / "integration_ai_description.yaml").write_text(
        "product_categories:\n  reasoning: ''\n  siem: false\n",
        encoding="utf-8",
    )
    (ai_dir / "actions_ai_description.yaml").write_text(
        "ValidAction:\n"
        "  ai_description: 'General Description \\n Flow Description \\n Additional Notes'\n"
        "  ai_short_description: 'Valid short.'\n"
        "  parameters_description: 'There are no parameters for this action'\n",
        encoding="utf-8",
    )
    engine = EvaluationEngine()
    report = engine.evaluate_integration(
        integration_id="mock_meta",
        src=tmp_path,
        use_llm=False,
    )
    assert not any(r.action_id == "product_categories" for r in report.results)
    assert any(r.action_id == "ValidAction" for r in report.results)


def test_heuristic_fallback_summary_notification_logged(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that a summary notification is logged when rule evaluation falls back to heuristics."""
    integration_dir = tmp_path / "mock_fallback"
    ai_dir = integration_dir / "resources" / "ai"
    ai_dir.mkdir(parents=True)
    (ai_dir / "actions_ai_description.yaml").write_text(
        "ValidAction:\n"
        "  ai_description: 'General Description \\n Flow Description \\n Additional Notes'\n"
        "  ai_short_description: 'Valid short description.'\n"
        "  parameters_description: 'There are no parameters for this action'\n",
        encoding="utf-8",
    )
    engine = EvaluationEngine()
    with caplog.at_level("WARNING"):
        engine.evaluate_integration(
            integration_id="mock_fallback",
            src=tmp_path,
            use_llm=False,
        )
    assert "RE-RUN RECOMMENDED" in caplog.text
    assert "fell back to heuristic verification" in caplog.text
    assert "Tip: Re-run 'mp describe evaluate mock_fallback --use-llm'" in caplog.text
