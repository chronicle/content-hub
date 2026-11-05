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

"""Unit tests for ``ri_breaking_change_check.py`` built from small synthetic trees.

Run with ``pytest .github/scripts/test_ri_breaking_change_check.py``.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ri_breaking_change_check as bcc  # noqa: E402

ROOT = "content/response_integrations/third_party/community/acme"
DEFINITION = f"{ROOT}/definition.yaml"
ACTION = f"{ROOT}/actions/GetThing.yaml"
CONNECTOR = f"{ROOT}/connectors/AlertsConnector.yaml"
JOB = f"{ROOT}/jobs/SyncJob.yaml"
RESULT = f"{ROOT}/resources/GetThing_JsonResult_example.json"
NOTES = f"{ROOT}/release_notes.yaml"

DEFINITION_YAML = """\
identifier: Acme
name: Acme
parameters:
- name: API Root
  type: string
  is_mandatory: true
  default_value: https://acme.example
- name: Verify SSL
  type: boolean
  is_mandatory: false
  default_value: 'True'
"""

ACTION_YAML = """\
name: Get Thing
integration_identifier: Acme
description: Gets a thing.
parameters:
-   name: Thing ID
    type: string
    is_mandatory: true
    default_value: ''
-   name: Mode
    type: ddl
    is_mandatory: false
    default_value: fast
    optional_values:
    - fast
    - slow
dynamic_results_metadata:
-   result_example_path: resources/GetThing_JsonResult_example.json
    result_name: JsonResult
    show_result: true
script_result_name: is_success
"""

CONNECTOR_YAML = """\
name: Acme - Alerts Connector
integration: Acme
parameters:
-   name: Max Hours Backwards
    type: integer
    is_mandatory: false
    default_value: 1
    mode: script
rules: []
is_connector_rules_supported: false
"""

JOB_YAML = """\
name: Sync Job
integration: Acme
parameters:
-   name: Interval
    type: integer
    is_mandatory: true
    default_value: 60
"""

RESULT_JSON = json.dumps({"id": "1", "status": "open", "owner": {"name": "x"}})

NOTES_YAML = """\
- description: NEW! Acme integration.
  version: 1.0
  item_name: Acme
  item_type: Integration
  publish_time: '2024-01-01'
"""

BASE_FILES: Mapping[str, str] = {
    DEFINITION: DEFINITION_YAML,
    ACTION: ACTION_YAML,
    CONNECTOR: CONNECTOR_YAML,
    JOB: JOB_YAML,
    RESULT: RESULT_JSON,
    NOTES: NOTES_YAML,
    # A second, untouched integration to prove the check only looks at touched directories.
    "content/response_integrations/google/other/definition.yaml": "identifier: Other\nname: Other\nparameters: []\n",
    "content/response_integrations/google/other/actions/Ping.yaml": "name: Ping\nintegration_identifier: Other\n",
}


def run(
    head_overrides: Mapping[str, str | None], *, labels: str = "", changed: list[str] | None = None
) -> bcc.CheckResult:
    """Run the check on BASE_FILES vs BASE_FILES + overrides (``None`` deletes a file)."""
    head_files = {**BASE_FILES}
    for path, content in head_overrides.items():
        if content is None:
            head_files.pop(path, None)
        else:
            head_files[path] = content
    changed_files = changed if changed is not None else sorted(set(head_overrides))
    return bcc.run_check(
        changed_files,
        bcc.DictTree(BASE_FILES),
        bcc.DictTree(head_files),
        labels=bcc.parse_labels(labels),
    )


def rule_ids(result: bcc.CheckResult, *, blocking_only: bool = False) -> list[str]:
    return [f.rule.rule_id for f in result.findings if f.is_blocking or not blocking_only]


def mandatory_param(name: str, type_: str = "string") -> str:
    return f"- name: {name}\n  type: {type_}\n  is_mandatory: true\n"


def release_note(description: str, **extra: object) -> str:
    lines = [f"- description: {description}", "  version: 2.0", "  item_name: Acme", "  item_type: Integration"]
    lines += [f"  {key}: {value}" for key, value in extra.items()]
    return "\n".join(lines) + "\n"


MODE_PARAM_YAML = (
    "-   name: Mode\n    type: ddl\n    is_mandatory: false\n    default_value: fast\n"
    "    optional_values:\n    - fast\n    - slow\n"
)
RESULTS_METADATA_YAML = (
    "dynamic_results_metadata:\n-   result_example_path: resources/GetThing_JsonResult_example.json\n"
    "    result_name: JsonResult\n    show_result: true\n"
)


# --------------------------------------------------------------------------- #
# No-op / routine changes
# --------------------------------------------------------------------------- #
def test_untouched_or_cosmetic_changes_pass() -> None:
    result = run({ACTION: ACTION_YAML.replace("Gets a thing.", "Gets a thing, quickly.")})
    assert result.exit_code == 0
    assert result.findings == []
    assert [r.root for r in result.reports] == [ROOT]


def test_files_outside_an_integration_are_ignored() -> None:
    result = run({"content/response_integrations/README.md": "hello"})
    assert result.exit_code == 0
    assert result.reports == []


def test_new_integration_is_not_compared() -> None:
    new_root = "content/response_integrations/google/brand_new"
    result = run({
        f"{new_root}/definition.yaml": "identifier: BrandNew\nname: Brand New\nparameters:\n" + mandatory_param("Key"),
        f"{new_root}/actions/Do.yaml": "name: Do\nintegration_identifier: BrandNew\nparameters:\n"
        + mandatory_param("X"),
    })
    assert result.exit_code == 0
    assert result.findings == []


def test_new_component_may_have_mandatory_parameters() -> None:
    new_action = f"{ROOT}/actions/Create.yaml"
    result = run({
        new_action: "name: Create Thing\nintegration_identifier: Acme\nparameters:\n" + mandatory_param("Body")
    })
    assert result.exit_code == 0
    assert result.findings == []


def test_adding_optional_parameter_and_result_keys_passes() -> None:
    head_action = ACTION_YAML.replace(
        "dynamic_results_metadata:",
        "-   name: Limit\n    type: string\n    is_mandatory: false\n    default_value: 10\ndynamic_results_metadata:",
    )
    head_result = json.dumps({"id": "1", "status": "open", "owner": {"name": "x"}, "extra": True})
    result = run({ACTION: head_action, RESULT: head_result})
    assert result.exit_code == 0
    assert result.findings == []


# --------------------------------------------------------------------------- #
# Rule 1: components and integration identity
# --------------------------------------------------------------------------- #
def test_removed_action_fails() -> None:
    result = run({ACTION: None})
    assert rule_ids(result, blocking_only=True) == ["component-removed"]
    assert result.exit_code == 1
    assert 'action "Get Thing"' in result.findings[0].component


def test_removed_connector_and_job_fail() -> None:
    result = run({CONNECTOR: None, JOB: None})
    assert sorted(rule_ids(result, blocking_only=True)) == ["component-removed", "component-removed"]
    assert {f.component for f in result.findings} == {'connector "Acme - Alerts Connector"', 'job "Sync Job"'}


def test_component_name_change_fails_and_points_at_new_name() -> None:
    result = run({ACTION: ACTION_YAML.replace("name: Get Thing", "name: Fetch Thing")})
    assert rule_ids(result, blocking_only=True) == ["component-name-changed"]
    finding = result.findings[0]
    assert "`Get Thing` to `Fetch Thing`" in finding.detail
    assert finding.file == ACTION
    assert finding.line == 1


def test_component_file_rename_with_same_name_is_only_a_warning() -> None:
    renamed = f"{ROOT}/actions/GetThingV2.yaml"
    result = run({ACTION: None, renamed: ACTION_YAML})
    assert rule_ids(result) == ["component-file-renamed"]
    assert result.exit_code == 0


def test_mass_file_renames_are_reported_once_per_kind() -> None:
    """Snake-case migrations rename every file (e.g. #930, #1015); one warning per kind keeps the noise down."""
    new_action = f"{ROOT}/actions/Create.yaml"
    base_files = {**BASE_FILES, new_action: "name: Create\nintegration_identifier: Acme\nparameters: []\n"}
    head_files = {k: v for k, v in base_files.items() if k not in {ACTION, new_action, CONNECTOR}}
    head_files[f"{ROOT}/actions/get_thing.yaml"] = ACTION_YAML
    head_files[f"{ROOT}/actions/create.yaml"] = base_files[new_action]
    head_files[f"{ROOT}/connectors/alerts_connector.yaml"] = CONNECTOR_YAML
    result = bcc.run_check([ACTION, CONNECTOR], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[])
    assert rule_ids(result) == ["component-file-renamed", "component-file-renamed"]
    assert {f.component for f in result.findings} == {"2 action file(s)", "1 connector file(s)"}
    assert result.exit_code == 0


def test_component_integration_identifier_change_fails() -> None:
    result = run({ACTION: ACTION_YAML.replace("integration_identifier: Acme", "integration_identifier: AcmeV2")})
    assert rule_ids(result, blocking_only=True) == ["component-integration-changed"]


def test_fixing_component_integration_link_to_match_definition_passes() -> None:
    """Tuned on replay (#1016): correcting a wrong `integration` to the integration's own identifier is a fix."""
    base_files = {**BASE_FILES, CONNECTOR: CONNECTOR_YAML.replace("integration: Acme", "integration: Acme Inc")}
    head_files = {**base_files, CONNECTOR: CONNECTOR_YAML}
    result = bcc.run_check([CONNECTOR], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[])
    assert result.findings == []


def test_integration_identifier_and_name_change_fail() -> None:
    result = run({
        DEFINITION: DEFINITION_YAML.replace("identifier: Acme", "identifier: Acme2").replace(
            "name: Acme", "name: Acme 2"
        )
    })
    assert sorted(rule_ids(result, blocking_only=True)) == [
        "integration-identifier-changed",
        "integration-name-changed",
    ]


def test_integration_removed_fails() -> None:
    result = run({path: None for path in BASE_FILES if path.startswith(ROOT)})
    assert rule_ids(result) == ["integration-removed"]
    assert result.exit_code == 1


def test_integration_moved_is_compared_at_new_location() -> None:
    new_root = "content/response_integrations/third_party/partner/acme"
    moved = {path: None for path in BASE_FILES if path.startswith(ROOT)}
    moved.update({
        path.replace(ROOT, new_root): content for path, content in BASE_FILES.items() if path.startswith(ROOT)
    })
    moved[f"{new_root}/actions/GetThing.yaml"] = ACTION_YAML.replace("-   name: Mode\n", "-   name: Mode 2\n")
    result = run(moved)
    assert sorted(rule_ids(result)) == ["integration-moved", "parameter-removed"]
    assert result.exit_code == 1
    assert result.reports[0].root == new_root


# --------------------------------------------------------------------------- #
# Rule 2: parameters
# --------------------------------------------------------------------------- #
def test_removed_parameter_fails() -> None:
    assert MODE_PARAM_YAML in ACTION_YAML
    result = run({ACTION: ACTION_YAML.replace(MODE_PARAM_YAML, "")})
    assert rule_ids(result, blocking_only=True) == ["parameter-removed"]
    assert "`Mode`" in result.findings[0].detail


def test_parameter_made_mandatory_fails() -> None:
    head = ACTION_YAML.replace("    type: ddl\n    is_mandatory: false", "    type: ddl\n    is_mandatory: true")
    result = run({ACTION: head})
    assert rule_ids(result, blocking_only=True) == ["parameter-made-mandatory"]
    assert result.findings[0].file == ACTION
    assert result.findings[0].line == 9  # the `name: Mode` line in the head file


def test_new_mandatory_parameter_on_existing_component_fails() -> None:
    head = ACTION_YAML.replace(
        "dynamic_results_metadata:",
        "-   name: Tenant\n    type: string\n    is_mandatory: true\ndynamic_results_metadata:",
    )
    result = run({ACTION: head})
    assert rule_ids(result, blocking_only=True) == ["new-mandatory-parameter"]
    # A "no default" spelling such as `null` or '' does not count as a default.
    result = run({
        ACTION: head.replace(
            "    is_mandatory: true\ndynamic", "    is_mandatory: true\n    default_value: null\ndynamic"
        )
    })
    assert rule_ids(result, blocking_only=True) == ["new-mandatory-parameter"]


def test_new_mandatory_parameter_with_default_is_only_a_warning() -> None:
    """Tuned on replay: 'Add <flag> parameter' PRs add mandatory booleans with defaults (e.g. #1231)."""
    head = ACTION_YAML.replace(
        "dynamic_results_metadata:",
        "-   name: Disable Overflow\n    type: boolean\n    is_mandatory: true\n    default_value: false\n"
        "dynamic_results_metadata:",
    )
    result = run({ACTION: head})
    assert rule_ids(result) == ["new-mandatory-parameter-with-default"]
    assert result.exit_code == 0


def test_parameter_type_change_fails_but_case_differences_do_not() -> None:
    result = run({ACTION: ACTION_YAML.replace("    type: ddl\n", "    type: DDL\n")})
    assert result.findings == []
    result = run({ACTION: ACTION_YAML.replace("    type: ddl\n", "    type: string\n")})
    assert rule_ids(result, blocking_only=True) == ["parameter-type-changed"]


def test_string_to_password_is_only_a_warning() -> None:
    """Tuned on replay: hardening an API key from string to password keeps the stored value (e.g. #684)."""
    result = run({
        DEFINITION: DEFINITION_YAML.replace("- name: API Root\n  type: string", "- name: API Root\n  type: password")
    })
    assert rule_ids(result) == ["parameter-type-masked"]
    assert result.exit_code == 0
    # The other direction exposes a secret and is still a hard failure.
    result = run({CONNECTOR: CONNECTOR_YAML.replace("type: integer", "type: password")})
    assert rule_ids(result, blocking_only=True) == ["parameter-type-changed"]


def test_action_string_integer_alias_is_not_a_type_change() -> None:
    result = run({
        ACTION: ACTION_YAML.replace("-   name: Thing ID\n    type: string", "-   name: Thing ID\n    type: integer")
    })
    assert result.findings == []
    # ...but for connectors/jobs/integration parameters they are distinct platform types.
    result = run({CONNECTOR: CONNECTOR_YAML.replace("type: integer", "type: string")})
    assert rule_ids(result, blocking_only=True) == ["parameter-type-changed"]


def test_default_value_change_is_a_warning_and_ignores_cosmetic_differences() -> None:
    result = run({ACTION: ACTION_YAML.replace("default_value: fast", "default_value: slow")})
    assert rule_ids(result) == ["default-value-changed"]
    assert result.exit_code == 0
    cosmetic = DEFINITION_YAML.replace("default_value: 'True'", "default_value: true").replace(
        "default_value: https://acme.example", "default_value: '  https://acme.example '"
    )
    assert run({DEFINITION: cosmetic}).findings == []
    assert run({JOB: JOB_YAML.replace("default_value: 60", "default_value: '60'")}).findings == []


def test_removed_optional_value_is_a_warning() -> None:
    result = run({ACTION: ACTION_YAML.replace("    - slow\n", "")})
    assert rule_ids(result) == ["optional-value-removed"]
    assert result.exit_code == 0


def test_integration_level_parameters_follow_the_same_rules() -> None:
    head = DEFINITION_YAML.replace(
        "- name: Verify SSL\n  type: boolean\n  is_mandatory: false",
        "- name: Verify SSL\n  type: boolean\n  is_mandatory: true",
    )
    head += "- name: Tenant\n  type: string\n  is_mandatory: true\n"
    result = run({DEFINITION: head})
    assert sorted(rule_ids(result, blocking_only=True)) == ["new-mandatory-parameter", "parameter-made-mandatory"]
    assert all(f.component == "integration" for f in result.findings)
    assert all(f.file == DEFINITION for f in result.findings)


def test_connector_and_job_parameter_regressions_fail() -> None:
    result = run({
        CONNECTOR: CONNECTOR_YAML.replace("is_mandatory: false", "is_mandatory: true"),
        JOB: JOB_YAML.replace("-   name: Interval", "-   name: Period"),
    })
    # Renaming a job parameter is reported as a removal (plus a warning for the new mandatory-with-default one).
    assert sorted(rule_ids(result, blocking_only=True)) == ["parameter-made-mandatory", "parameter-removed"]
    assert "new-mandatory-parameter-with-default" in rule_ids(result)
    assert {f.component for f in result.findings} == {'connector "Acme - Alerts Connector"', 'job "Sync Job"'}


# --------------------------------------------------------------------------- #
# Rule 3: JSON result examples
# --------------------------------------------------------------------------- #
def test_removed_result_key_fails() -> None:
    result = run({RESULT: json.dumps({"id": "1", "owner": {"name": "x"}})})
    assert rule_ids(result, blocking_only=True) == ["result-keys-removed"]
    assert "`status`" in result.findings[0].detail
    assert result.findings[0].file == RESULT


def test_nested_key_removal_is_ignored() -> None:
    result = run({RESULT: json.dumps({"id": "1", "status": "open", "owner": {}})})
    assert result.findings == []


def test_result_shape_change_fails() -> None:
    result = run({RESULT: json.dumps([{"id": "1", "status": "open", "owner": {}}])})
    assert rule_ids(result, blocking_only=True) == ["result-shape-changed"]


def test_list_results_use_union_of_item_keys() -> None:
    base_list = json.dumps([{"id": 1, "a": 1}, {"id": 2, "b": 2}])
    head_ok = json.dumps([{"id": 1, "a": 1, "b": 2}])
    head_bad = json.dumps([{"id": 1, "a": 1}])
    base_files = {**BASE_FILES, RESULT: base_list}
    ok = bcc.run_check([RESULT], bcc.DictTree(base_files), bcc.DictTree({**base_files, RESULT: head_ok}), labels=[])
    assert ok.findings == []
    bad = bcc.run_check([RESULT], bcc.DictTree(base_files), bcc.DictTree({**base_files, RESULT: head_bad}), labels=[])
    assert rule_ids(bad, blocking_only=True) == ["result-keys-removed"]
    assert "`b`" in bad.findings[0].detail


def test_entity_results_compare_keys_inside_entity_result() -> None:
    base = json.dumps([{"Entity": "1.1.1.1", "EntityResult": {"score": 1, "country": "US"}}])
    head_ok = json.dumps([{"Entity": "1.1.1.1", "EntityResult": {"score": 1, "country": "US", "asn": 13335}}])
    head_bad = json.dumps([{"Entity": "1.1.1.1", "EntityResult": {"score": 1}}])
    base_files = {**BASE_FILES, RESULT: base}
    ok = bcc.run_check([RESULT], bcc.DictTree(base_files), bcc.DictTree({**base_files, RESULT: head_ok}), labels=[])
    assert ok.findings == []
    bad = bcc.run_check([RESULT], bcc.DictTree(base_files), bcc.DictTree({**base_files, RESULT: head_bad}), labels=[])
    assert rule_ids(bad, blocking_only=True) == ["result-keys-removed"]
    assert "`country`" in bad.findings[0].detail


def test_result_shape_helper_handles_all_shapes() -> None:
    assert bcc.result_shape({"a": 1, "b": 2}) == ("object", frozenset({"a", "b"}))
    assert bcc.result_shape([{"a": 1}, {"b": 2}, "scalar"]) == ("list", frozenset({"a", "b"}))
    assert bcc.result_shape({"Entity": "x", "EntityResult": [{"k": 1}, {"j": 2}]}) == ("object", frozenset({"k", "j"}))
    assert bcc.result_shape([]) == ("list", frozenset())
    assert bcc.result_shape("text") == ("scalar", frozenset())
    assert bcc.result_shape(None) == ("scalar", frozenset())


def test_removed_result_example_is_a_warning() -> None:
    assert RESULTS_METADATA_YAML in ACTION_YAML
    result = run({ACTION: ACTION_YAML.replace(RESULTS_METADATA_YAML, ""), RESULT: None})
    assert rule_ids(result) == ["result-example-removed"]
    assert result.exit_code == 0


def test_script_result_name_change_is_a_warning() -> None:
    result = run({ACTION: ACTION_YAML.replace("script_result_name: is_success", "script_result_name: success")})
    assert rule_ids(result) == ["script-result-name-changed"]
    assert result.exit_code == 0


# --------------------------------------------------------------------------- #
# Escape hatches
# --------------------------------------------------------------------------- #
def test_breaking_change_label_waives_failures() -> None:
    result = run({ACTION: None}, labels="community, Breaking-Change ")
    assert result.label_hatch is True
    assert result.exit_code == 0
    assert result.findings[0].severity is bcc.Severity.ERROR
    assert result.findings[0].waived_by == "label `breaking-change`"
    assert "waived" in bcc.summary_markdown(result)


def test_regressive_release_note_waives_failures_for_that_integration() -> None:
    notes = NOTES_YAML + release_note("'Removed the Get Thing action. This is a REGRESSIVE change.'")
    result = run({ACTION: None, NOTES: notes})
    assert result.exit_code == 0
    assert result.reports[0].release_note_hatch.startswith("Removed the Get Thing action")
    assert result.findings[0].waived_by == "release note marked regressive"


def test_regressive_flag_in_release_note_also_counts() -> None:
    notes = NOTES_YAML + release_note("Dropped legacy parameters.", regressive="true")
    result = run({ACTION: None, NOTES: notes})
    assert result.exit_code == 0
    assert result.findings[0].waived_by == "release note marked regressive"


def test_pre_existing_regressive_note_does_not_waive() -> None:
    base_files = {**BASE_FILES, NOTES: NOTES_YAML + release_note("Old breaking change.")}
    head_files = {**base_files}
    del head_files[ACTION]
    result = bcc.run_check([ACTION], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[])
    assert result.exit_code == 1
    assert result.reports[0].release_note_hatch is None


def test_release_note_hatch_only_applies_to_its_own_integration() -> None:
    notes = NOTES_YAML + release_note("breaking change in acme")
    other_action = "content/response_integrations/google/other/actions/Ping.yaml"
    result = run({NOTES: notes, other_action: None})
    assert result.exit_code == 1
    assert [f.integration for f in result.blocking] == ["content/response_integrations/google/other"]


# --------------------------------------------------------------------------- #
# Robustness
# --------------------------------------------------------------------------- #
def test_unparseable_yaml_is_a_warning_not_a_crash() -> None:
    result = run({ACTION: "name: [unclosed\nparameters: - :\n\t- bad"})
    # The broken file must not cascade into a "component removed" failure.
    assert rule_ids(result) == ["parse-error"]
    assert result.exit_code == 0


def test_unparseable_definition_and_json_are_warnings() -> None:
    result = run({DEFINITION: "identifier: Acme\nname: [", RESULT: "{not json"})
    assert sorted(rule_ids(result)) == ["parse-error", "parse-error"]
    assert result.exit_code == 0


def test_windows_line_endings_bom_and_anchors_are_handled() -> None:
    head = "\ufeff" + ACTION_YAML.replace("\n", "\r\n").replace("    default_value: ''", "    default_value: &d ''")
    head = head.replace("default_value: fast", "default_value: *d")
    result = run({ACTION: head})
    assert rule_ids(result) == ["default-value-changed"]


def test_non_mapping_component_yaml_is_skipped_with_warning() -> None:
    result = run({ACTION: "- just\n- a list\n"})
    assert rule_ids(result) == ["parse-error"]


def test_name_lines_finds_first_occurrence() -> None:
    lines = bcc.name_lines("name: Top\nparameters:\n-   name: 'Quoted Param'\n    item_name: nope\n-   name: Top\n")
    assert lines == {"Top": 1, "Quoted Param": 3}


def test_normalize_scalar() -> None:
    assert bcc.normalize_scalar(None) == bcc.normalize_scalar("")
    assert bcc.normalize_scalar(True) == bcc.normalize_scalar("TRUE")
    assert bcc.normalize_scalar(4) == bcc.normalize_scalar("4") == bcc.normalize_scalar(4.0)
    assert bcc.normalize_scalar(" a  b ") == bcc.normalize_scalar("A B")
    assert bcc.normalize_scalar("1.5") != bcc.normalize_scalar("2")
    assert bcc.normalize_scalar("nan") == "nan"


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def test_annotation_format_and_escaping() -> None:
    finding = bcc.Finding(
        bcc.Rule.PARAMETER_REMOVED,
        ROOT,
        'action "Get, Thing"',
        "Parameter `A:B` was removed.\nSecond line 100%",
        file=ACTION,
        line=7,
    )
    text = bcc.annotation(finding)
    assert text.startswith(f"::error file={ACTION},line=7,title=Breaking change%3A parameter-removed::")
    assert "%0A" in text and "%25" in text
    assert "\n" not in text
    waived = finding.waived("label `breaking-change`")
    assert bcc.annotation(waived).startswith("::warning ")


def test_summary_table_and_json_report() -> None:
    result = run({ACTION: ACTION_YAML.replace("default_value: fast", "default_value: slow"), JOB: None})
    markdown = bcc.summary_markdown(result)
    assert "**Result: FAIL** - 1 breaking change(s), 1 warning(s)." in markdown
    assert '| `acme` | job "Sync Job" | `component-removed` | FAIL |' in markdown
    assert '| `acme` | action "Get Thing" | `default-value-changed` | warning |' in markdown
    assert "What this check is and how to fix findings" in markdown
    report = bcc.json_report(result)
    assert report["exit_code"] == 1
    assert {f["rule"] for f in report["findings"]} == {"component-removed", "default-value-changed"}


def test_cli_end_to_end_with_git(tmp_path: Path) -> None:
    """Exercise the git-backed path: two commits in a throwaway repository."""
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    git = lambda *args: subprocess.run(  # noqa: E731
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "HOME": str(tmp_path),
            "PATH": "/usr/bin:/bin",
        },
    )
    git("init", "-q", "-b", "main")

    def write_all(files: Mapping[str, str]) -> None:
        for name in list(p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts):
            name.unlink()
        for path, content in files.items():
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    write_all(BASE_FILES)
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    base_sha = git("rev-parse", "HEAD").stdout.strip()
    head_files = {**BASE_FILES}
    del head_files[JOB]
    write_all(head_files)
    git("add", "-A")
    git("commit", "-q", "-m", "remove job")
    head_sha = git("rev-parse", "HEAD").stdout.strip()

    summary = tmp_path / "summary.md"
    json_path = tmp_path / "report.json"
    code = bcc.main([
        "--base",
        base_sha,
        "--head",
        head_sha,
        "--repo-root",
        str(repo),
        "--summary-file",
        str(summary),
        "--json",
        str(json_path),
        "--no-annotations",
    ])
    assert code == 1
    assert "component-removed" in summary.read_text()
    assert json.loads(json_path.read_text())["merge_base"] == base_sha

    code = bcc.main([
        "--base",
        base_sha,
        "--head",
        head_sha,
        "--repo-root",
        str(repo),
        "--labels",
        "breaking-change",
        "--summary-file",
        str(summary),
    ])
    assert code == 0


def test_cli_rejects_unknown_commits(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    assert (
        bcc.main([
            "--base",
            "0" * 40,
            "--head",
            "1" * 40,
            "--repo-root",
            str(tmp_path),
            "--summary-file",
            str(tmp_path / "s.md"),
        ])
        == 2
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
