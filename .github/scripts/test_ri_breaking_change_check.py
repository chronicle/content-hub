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


@pytest.mark.parametrize(
    "description",
    [
        "Non-breaking: added the Limit parameter.",
        "A groundbreaking new connector.",
        "This is not a breaking change.",
        "No breaking changes; non regressive refactor.",
        "non-regressive fix for pagination",
        "Unbreakingly nice",
    ],
)
def test_negated_or_embedded_breaking_words_do_not_waive(description: str) -> None:
    assert bcc.mentions_breaking_change(description) is False
    result = run({ACTION: None, NOTES: NOTES_YAML + release_note(f"'{description}'")})
    assert result.exit_code == 1
    assert result.reports[0].release_note_hatch is None


@pytest.mark.parametrize(
    "description",
    ["BREAKING: removed Get Thing", "REGRESSIVE! - rewritten", "Regressive - removed Get Thing.", "(breaking)"],
)
def test_breaking_words_as_whole_words_do_waive(description: str) -> None:
    assert bcc.mentions_breaking_change(description) is True
    result = run({ACTION: None, NOTES: NOTES_YAML + release_note(f"'{description}'")})
    assert result.exit_code == 0


def test_editing_an_existing_note_to_declare_the_regression_counts_as_added() -> None:
    """The note key includes the description and the flag, so rewriting an old entry to declare it is a declaration."""
    old = release_note("Fixed pagination.", regressive="false")
    base_files = {**BASE_FILES, NOTES: NOTES_YAML + old}
    head_files = {**base_files, NOTES: NOTES_YAML + old.replace("Fixed pagination.", "REGRESSIVE - Fixed pagination.")}
    del head_files[ACTION]
    result = bcc.run_check([ACTION, NOTES], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[])
    assert result.exit_code == 0
    assert result.reports[0].release_note_hatch == "REGRESSIVE - Fixed pagination."
    head_files[NOTES] = NOTES_YAML + old.replace("regressive: false", "regressive: true")
    result = bcc.run_check([ACTION, NOTES], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[])
    assert result.exit_code == 0
    assert result.reports[0].release_note_hatch == "Fixed pagination."
    # Reordering or re-quoting existing notes does not add anything.
    head_files[NOTES] = old + NOTES_YAML.replace("NEW! Acme integration.", "'NEW! Acme integration.'")
    result = bcc.run_check([ACTION, NOTES], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[])
    assert result.exit_code == 1
    assert result.reports[0].release_note_hatch is None


def test_regressive_string_values_follow_as_bool() -> None:
    assert bcc.as_bool("true") is bcc.as_bool("True") is bcc.as_bool(" YES ") is bcc.as_bool("1") is True
    assert bcc.as_bool("false") is bcc.as_bool("0") is bcc.as_bool("") is bcc.as_bool(None) is bcc.as_bool([1]) is False
    assert bcc.release_note_hatch([], [{"description": "x", "regressive": "false"}]) is None
    assert bcc.release_note_hatch([], [{"description": "x", "regressive": "True"}]) == "x"
    assert bcc.release_note_hatch([], [{"description": None, "regressive": 1}]) == "regressive: true"


def test_labels_are_parsed_from_json_or_commas_and_matched_exactly() -> None:
    assert bcc.parse_labels('["community", "Breaking-Change", " has, comma "]') == [
        "community",
        "Breaking-Change",
        "has, comma",
    ]
    assert bcc.parse_labels("[]") == bcc.parse_labels("") == bcc.parse_labels(None) == bcc.parse_labels(" , ") == []
    assert bcc.parse_labels("[not json") == ["[not json"]
    assert bcc.parse_labels("a, breaking-change ,,b") == ["a", "breaking-change", "b"]
    assert bcc.has_breaking_label(bcc.parse_labels('["non-breaking-change", "breaking-changes"]')) is False
    assert bcc.has_breaking_label(bcc.parse_labels('["x", " BREAKING-CHANGE "]')) is True
    assert run({ACTION: None}, labels='["non-breaking-change"]').exit_code == 1
    assert run({ACTION: None}, labels='["breaking-change"]').exit_code == 0


def test_hatches_waive_errors_but_leave_warnings_untouched() -> None:
    result = run(
        {ACTION: ACTION_YAML.replace("default_value: fast", "default_value: slow"), JOB: None}, labels="breaking-change"
    )
    by_rule = {f.rule.rule_id: f for f in result.findings}
    assert by_rule["component-removed"].waived_by == "label `breaking-change`"
    assert by_rule["default-value-changed"].waived_by is None
    assert "PASS with waived breaking changes" in bcc.summary_markdown(result)


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


def test_names_are_compared_exactly_with_a_hint_for_near_misses() -> None:
    """The platform matches names byte for byte, so trimming whitespace or changing case is a rename."""
    base_files = {
        **BASE_FILES,
        CONNECTOR: CONNECTOR_YAML.replace("name: Max Hours Backwards", "name: 'Max Hours Backwards '"),
        ACTION: ACTION_YAML.replace("name: Get Thing\n", "name: 'Get Thing  '\n"),
    }
    head_files = {**base_files, CONNECTOR: CONNECTOR_YAML.replace("is_mandatory: false", "is_mandatory: true")}
    result = bcc.run_check([CONNECTOR], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[])
    assert rule_ids(result, blocking_only=True) == ["parameter-removed"]
    assert "new-mandatory-parameter-with-default" in rule_ids(result)  # the trimmed name is a new parameter
    removed = next(f for f in result.findings if f.rule is bcc.Rule.PARAMETER_REMOVED)
    assert removed.detail == (
        "Parameter `Max Hours Backwards ` was removed. Found `Max Hours Backwards` instead; names must match exactly"
        " (case and surrounding whitespace)."
    )
    # Case-only parameter rename.
    result = bcc.run_check(
        [JOB],
        bcc.DictTree(BASE_FILES),
        bcc.DictTree({**BASE_FILES, JOB: JOB_YAML.replace("name: Interval", "name: interval")}),
        labels=[],
    )
    assert "Found `interval` instead" in result.findings[0].detail
    # Component name trimmed: a rename, with the hint and the line of the new name.
    result = bcc.run_check(
        [ACTION], bcc.DictTree(base_files), bcc.DictTree({**base_files, ACTION: ACTION_YAML}), labels=[]
    )
    assert rule_ids(result, blocking_only=True) == ["component-name-changed"]
    assert result.findings[0].detail.endswith("names must match exactly (case and surrounding whitespace).")
    assert result.findings[0].line == 1
    # A blank name is "no name", a non-scalar name is ignored, and parameters keep their line numbers.
    assert bcc.as_name("   ") is bcc.as_name(None) is bcc.as_name({"a": 1}) is None
    assert bcc.as_name(" X ") == " X "
    params = bcc.parse_parameters(
        [{"name": " Q "}, {"name": ""}, {"type": "string"}], bcc.name_lines("- name: ' Q '\n")
    )
    assert [(p.name, p.line) for p in params] == [(" Q ", 1)]


def test_empty_example_placeholders_are_not_compared() -> None:
    """``{}``/``[]`` mean "no example" (``mp`` maps ``{}`` to none), so replacing them cannot remove anything."""
    for placeholder in ("{}", "[]"):
        base_files = {**BASE_FILES, RESULT: placeholder}
        for head_json in (json.dumps([{"a": 1}]), json.dumps({"a": 1}), "[]", "{}"):
            head_files = {**base_files, RESULT: head_json}
            assert bcc.run_check([RESULT], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[]).findings == []
        head_files = {**base_files, RESULT: None, ACTION: ACTION_YAML.replace(RESULTS_METADATA_YAML, "")}
        head_files.pop(RESULT)
        assert bcc.run_check([RESULT], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[]).findings == []
    # Emptying a real example still counts as losing its keys.
    result = run({RESULT: "{}"})
    assert rule_ids(result, blocking_only=True) == ["result-keys-removed"]


def test_result_example_file_removed_while_still_referenced_is_a_warning() -> None:
    result = run({RESULT: None})
    assert rule_ids(result) == ["result-example-removed"]
    assert result.exit_code == 0
    assert result.findings[0].file == ACTION


def test_many_removed_result_keys_are_truncated_in_the_detail() -> None:
    keys = {f"key{i:02d}": i for i in range(15)}
    base_files = {**BASE_FILES, RESULT: json.dumps(keys)}
    head_files = {**base_files, RESULT: json.dumps({"key00": 0})}
    result = bcc.run_check([RESULT], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[])
    detail = result.findings[0].detail
    assert detail.count("`key") == bcc.MAX_LISTED_KEYS
    assert detail.endswith("(+4 more).")


def test_component_files_are_discovered_like_mp_does() -> None:
    """``mp`` loads ``*.yaml`` recursively below actions/connectors/jobs; ``.yml`` files are not components."""
    nested = f"{ROOT}/actions/legacy/Old.yaml"
    yml = f"{ROOT}/actions/Ignored.yml"
    base_files = {
        **BASE_FILES,
        nested: "name: Old\nintegration_identifier: Acme\nparameters: []\n",
        yml: "name: Ignored\n",
    }
    head_files = {k: v for k, v in base_files.items() if k not in {nested, yml}}
    result = bcc.run_check([nested, yml], bcc.DictTree(base_files), bcc.DictTree(head_files), labels=[])
    assert rule_ids(result) == ["component-removed"]
    assert result.findings[0].component == 'action "Old"'


def test_name_lines_strips_quotes_and_whitespace() -> None:
    assert bcc.name_lines("name: '  Padded  '\n-   name: \"Q\"  \n") == {"Padded": 1, "Q": 2}


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
    assert {f["rule"]: f["blocking"] for f in report["findings"]} == {
        "component-removed": True,
        "default-value-changed": False,
    }
    assert report["integrations"] == [{"root": ROOT, "base_root": ROOT, "release_note_hatch": None}]


def test_annotation_properties_escape_commas_and_colons() -> None:
    finding = bcc.Finding(bcc.Rule.COMPONENT_REMOVED, ROOT, "x", "d", file=f"{ROOT}/actions/A,B:C.yaml", line=0)
    text = bcc.annotation(finding)
    assert text.startswith(f"::error file={ROOT}/actions/A%2CB%3AC.yaml,line=1,title=")
    assert text.count("::") == 2  # the opening and the separator only
    assert bcc.annotation(bcc.Finding(bcc.Rule.PARSE_ERROR, ROOT, "x", "d")).startswith("::warning title=parse-error::")


def test_summary_escapes_pipes_and_newlines_in_cells() -> None:
    result = run({ACTION: ACTION_YAML.replace("name: Get Thing", "name: Get | Thing")})
    rows = [line for line in bcc.summary_markdown(result).splitlines() if line.startswith("| `acme`")]
    assert len(rows) == 1
    assert rows[0].count("|") - rows[0].count("\\|") == 7  # six cells
    assert "Get \\| Thing" in rows[0]
    assert bcc._md("a\nb|c") == "a b\\|c"


def test_summary_lists_blocking_findings_first_and_caps_the_table() -> None:
    warning = bcc.Finding(bcc.Rule.DEFAULT_VALUE_CHANGED, ROOT, "a", "w")
    errors = [
        bcc.Finding(bcc.Rule.PARAMETER_REMOVED, ROOT, f"c{i:04d}", f"e{i}") for i in range(bcc.MAX_SUMMARY_ROWS + 5)
    ]
    result = bcc.CheckResult("b", "h", "m", [bcc.IntegrationReport(ROOT, ROOT, [warning, *errors])], label_hatch=False)
    ordered = bcc.sorted_findings(result)
    assert ordered[0].is_blocking and ordered[-1] is warning
    markdown = bcc.summary_markdown(result)
    rows = [line for line in markdown.splitlines() if line.startswith("| `acme`")]
    assert len(rows) == bcc.MAX_SUMMARY_ROWS
    assert all("FAIL" in row for row in rows)
    assert "... and 6 more finding(s)" in markdown
    assert len(markdown.encode()) < 1024 * 1024


class GitSandbox:
    """A throwaway git repository whose working tree is replaced wholesale by ``commit``."""

    def __init__(self, root: Path) -> None:
        import subprocess

        self.repo = root / "repo"
        self.repo.mkdir()
        self._env = {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "HOME": str(root),
            "PATH": "/usr/bin:/bin",
        }
        self._subprocess = subprocess
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str) -> str:
        return self._subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True, text=True, env=self._env
        ).stdout

    def commit(self, files: Mapping[str, str | bytes], message: str = "commit") -> str:
        for name in list(p for p in self.repo.rglob("*") if p.is_file() and ".git" not in p.parts):
            name.unlink()
        for path, content in files.items():
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD").strip()


def test_cli_end_to_end_with_git(tmp_path: Path) -> None:
    """Exercise the git-backed path: two commits in a throwaway repository."""
    sandbox = GitSandbox(tmp_path)
    base_sha = sandbox.commit(BASE_FILES, "base")
    head_files = {**BASE_FILES}
    del head_files[JOB]
    head_sha = sandbox.commit(head_files, "remove job")

    summary = tmp_path / "summary.md"
    json_path = tmp_path / "report.json"
    code = bcc.main([
        "--base",
        base_sha,
        "--head",
        head_sha,
        "--repo-root",
        str(sandbox.repo),
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
        str(sandbox.repo),
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


def test_cli_compares_against_the_merge_base_not_the_base_tip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Changes that landed on the base branch after the PR branched off must not be attributed to the PR."""
    sandbox = GitSandbox(tmp_path)
    fork_point = sandbox.commit(BASE_FILES, "fork point")
    # The PR branch: a harmless description tweak.
    sandbox.git("checkout", "-q", "-b", "pr")
    head_sha = sandbox.commit({**BASE_FILES, ACTION: ACTION_YAML.replace("Gets a thing.", "Gets it.")}, "pr")
    # Meanwhile main removed the job and a parameter; `base.sha` as reported by GitHub points at this tip.
    sandbox.git("checkout", "-q", "main")
    base_tip = sandbox.commit({k: v for k, v in BASE_FILES.items() if k != JOB}, "main moves on")

    json_path = tmp_path / "report.json"
    code = bcc.main([
        "--base",
        base_tip,
        "--head",
        head_sha,
        "--repo-root",
        str(sandbox.repo),
        "--json",
        str(json_path),
    ])
    report = json.loads(json_path.read_text())
    assert code == 0
    assert report["merge_base"] == fork_point
    assert report["findings"] == []
    assert "Comparing" in capsys.readouterr().out  # summary went to stdout because no --summary-file was given


def test_cli_blocking_annotations_come_first_and_unwritable_outputs_do_not_crash(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """GitHub shows at most 10 annotations per severity per step, so the blocking ones must be printed first."""
    sandbox = GitSandbox(tmp_path)
    base_sha = sandbox.commit(BASE_FILES, "base")
    head_files = {**BASE_FILES, ACTION: ACTION_YAML.replace("default_value: fast", "default_value: slow")}
    del head_files[JOB]
    head_sha = sandbox.commit(head_files, "head")
    missing_dir = tmp_path / "does-not-exist"
    code = bcc.main([
        "--base",
        base_sha,
        "--head",
        head_sha,
        "--repo-root",
        str(sandbox.repo),
        "--summary-file",
        str(missing_dir / "summary.md"),
        "--json",
        str(missing_dir / "report.json"),
    ])
    out = capsys.readouterr().out
    assert code == 1
    annotations = [line for line in out.splitlines() if line.startswith(("::error ", "::warning "))]
    assert [a.split(" ", 1)[0] for a in annotations] == ["::error", "::warning"]
    assert out.count("::warning::Could not write") == 2
    assert "**Result: FAIL**" in out  # the summary falls back to stdout


def test_git_layer_handles_special_characters_in_paths(tmp_path: Path) -> None:
    """Paths with spaces, quotes and non-ASCII characters must be read and diffed verbatim.

    ``git diff --name-only`` C-quotes such paths unless ``-z`` is used, and ``git cat-file --batch`` echoes a
    missing object's path back (``<rev>:<path with spaces> missing``), which used to be parsed as a size.
    """
    sandbox = GitSandbox(tmp_path)
    unicode_action = f'{ROOT}/actions/Ünïcode "Action".yaml'
    spaced_example = f"{ROOT}/resources/Get Thing_JsonResult_example.json"
    base_files = {
        **BASE_FILES,
        ACTION: ACTION_YAML.replace(
            "resources/GetThing_JsonResult_example.json", "resources/Get Thing_JsonResult_example.json"
        ),
        spaced_example: RESULT_JSON,
        unicode_action: "name: Ünïcode\nintegration_identifier: Acme\nparameters: []\n",
    }
    base_sha = sandbox.commit(base_files, "base")
    head_files = {k: v for k, v in base_files.items() if k not in {unicode_action, spaced_example}}
    head_sha = sandbox.commit(head_files, "head")

    repo = bcc.GitRepo(str(sandbox.repo))
    try:
        changed = repo.changed_files(base_sha, head_sha, bcc.RI_ROOT)
        assert sorted(changed) == sorted([unicode_action, spaced_example])
        assert repo.read_blob(head_sha, spaced_example) is None
        assert repo.read_blob(base_sha, spaced_example) == RESULT_JSON
        assert repo.read_blob(base_sha, unicode_action) is not None
        head_tree = bcc.GitTree(repo, head_sha)
        assert head_tree.list_files(bcc.RI_ROOT + "/")  # listing the RI root once...
        assert head_tree.list_files(ROOT + "/") == sorted(
            p for p in head_files if p.startswith(ROOT + "/")
        )  # serves this
        result = bcc.run_check(changed, bcc.GitTree(repo, base_sha), head_tree, labels=[])
    finally:
        repo.close()
    assert sorted(rule_ids(result)) == ["component-removed", "result-example-removed"]
    assert result.findings[0].file == unicode_action


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
