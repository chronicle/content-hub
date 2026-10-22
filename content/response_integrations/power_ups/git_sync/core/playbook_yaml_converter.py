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

import json
import logging
import re
from typing import TYPE_CHECKING, Any

import yaml

from .definitions import File

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.types import JSON, SingleJson

LOGGER = logging.getLogger(__name__)

# Enum/Integer mappings for Playbooks

PLAYBOOK_TYPE_MAP: dict[int, str] = {
    0: "playbook",
    1: "block",
}
PLAYBOOK_TYPE_MAP_REV: dict[str, int] = {v: k for k, v in PLAYBOOK_TYPE_MAP.items()}

CREATION_SOURCE_MAP: dict[int, str] = {
    0: "playbook_creation_source_unspecified",
    1: "user_or_api_initiated",
    2: "ai_generated_from_alert",
    3: "ai_generated_from_prompt",
}
CREATION_SOURCE_MAP_REV: dict[str, int] = {v: k for k, v in CREATION_SOURCE_MAP.items()}

ACCESS_LEVEL_MAP: dict[int, str] = {
    0: "no_access",
    1: "view",
    2: "edit",
}
ACCESS_LEVEL_MAP_REV: dict[str, int] = {v: k for k, v in ACCESS_LEVEL_MAP.items()}

TRIGGER_TYPE_MAP: dict[int, str] = {
    0: "vendor_name",
    1: "tag_name",
    2: "rule_name",
    3: "product_name",
    4: "network_name",
    5: "entity_details",
    6: "relation_details",
    7: "tracking_list",
    8: "all",
    9: "alert_trigger_value",
    10: "case_data",
    11: "get_inputs",
}
TRIGGER_TYPE_MAP_REV: dict[str, int] = {v: k for k, v in TRIGGER_TYPE_MAP.items()}

LOGICAL_OPERATOR_MAP: dict[int, str] = {
    0: "and",
    1: "or",
}
LOGICAL_OPERATOR_MAP_REV: dict[str, int] = {
    v: k for k, v in LOGICAL_OPERATOR_MAP.items()
}

MATCH_TYPE_MAP: dict[int, str] = {
    0: "equal",
    1: "contains",
    2: "starts_with",
    3: "greater_than",
    4: "less_than",
    5: "not_equal",
    6: "not_contains",
    7: "is_empty",
    8: "is_not_empty",
}
MATCH_TYPE_MAP_REV: dict[str, int] = {v: k for k, v in MATCH_TYPE_MAP.items()}

STEP_TYPE_MAP: dict[int, str] = {
    0: "action",
    1: "multi_choice_question",
    2: "previous_action",
    3: "case_data_condition",
    4: "condition",
    5: "block",
    6: "output",
    7: "parallel_actions_container",
    8: "for_each_start_loop",
    9: "for_each_end_loop",
}
STEP_TYPE_MAP_REV: dict[str, int] = {v: k for k, v in STEP_TYPE_MAP.items()}

OVERVIEW_TYPE_MAP: dict[int, str] = {
    0: "playbook_default",
    1: "regular",
    2: "system_alert",
    3: "system_case",
    4: "alert_type",
}
OVERVIEW_TYPE_MAP_REV: dict[str, int] = {v: k for k, v in OVERVIEW_TYPE_MAP.items()}

WIDGET_SIZE_MAP: dict[int, str] = {
    0: "small",
    1: "medium",
    2: "large",
}
WIDGET_SIZE_MAP_REV: dict[str, int] = {v: k for k, v in WIDGET_SIZE_MAP.items()}

STEP_FIELD_MAPPING: dict[str, str] = {
    "identifier": "identifier",
    "original_step_id": "originalStepIdentifier",
    "playbook_id": "parentWorkflowIdentifier",
    "parent_step_ids": "parentStepIdentifiers",
    "parent_step_id": "parentStepIdentifier",
    "previous_result_condition": "previousResultCondition",
    "destination_action_statuses": "destinationActionStatuses",
    "instance_name": "instanceName",
    "is_automatic": "isAutomatic",
    "name": "name",
    "is_skippable": "isSkippable",
    "description": "description",
    "action_provider": "actionProvider",
    "action_name": "actionName",
    "integration": "integration",
    "auto_skip_on_failure": "autoSkipOnFailure",
    "is_debug_mock_data": "isDebugMockData",
    "parent_container_id": "parentStepContainerId",
    "is_touched_by_ai": "isTouchedByAi",
    "start_loop_step_id": "startLoopStepIdentifier",
}

DEFINITION_FIELD_MAPPING: dict[str, str] = {
    "identifier": "identifier",
    "isEnabled": "is_enable",
    "version": "version",
    "name": "name",
    "description": "description",
    "priority": "priority",
    "categoryName": "category_name",
    "categoryId": "category",
    "environments": "environments",
    "isDebugMode": "is_debug_mode",
    "simulationClone": "simulation_clone",
}
DEFINITION_FIELD_MAPPING_REV: dict[str, str] = {
    v: k for k, v in DEFINITION_FIELD_MAPPING.items()
}

DEFINITION_HANDLED_KEYS: set[str] = set(DEFINITION_FIELD_MAPPING.keys()) | {
    "playbookType",
    "trigger",
    "steps",
    "stepsRelations",
    "id",
    "OverviewTemplatesDetails",
    "WidgetTemplates",
    "overviewTemplatesDetails",
    "widgetTemplates",
}
DEFINITION_HANDLED_NB_KEYS: set[str] = set(DEFINITION_FIELD_MAPPING_REV.keys()) | {
    "type",
}

TRIGGER_FIELD_MAPPING: dict[str, str] = {
    "identifier": "identifier",
    "isEnabled": "is_enabled",
    "definitionIdentifier": "playbook_id",
    "workflowName": "playbook_name",
    "environments": "environments",
}
TRIGGER_FIELD_MAPPING_REV: dict[str, str] = {
    v: k for k, v in TRIGGER_FIELD_MAPPING.items()
}

TRIGGER_HANDLED_KEYS: set[str] = {
    "id",
    "identifier",
    "isEnabled",
    "definitionIdentifier",
    "workflowName",
    "environments",
    "type",
    "Type",
    "logicalOperator",
    "LogicalOperator",
    "conditions",
    "Conditions",
}
TRIGGER_HANDLED_NB_KEYS: set[str] = {
    "identifier",
    "is_enabled",
    "playbook_id",
    "playbook_name",
    "environments",
    "type_",
    "logical_operator",
    "conditions",
}

OVERVIEW_TEMPLATE_MAPPING: dict[str, str] = {
    "Identifier": "identifier",
    "Name": "name",
    "Creator": "creator",
    "PlaybookDefinitionIdentifier": "playbook_id",
    "AlertRuleType": "alert_rule_type",
    "Roles": "roles",
}
OVERVIEW_TEMPLATE_MAPPING_REV: dict[str, str] = {
    v: k for k, v in OVERVIEW_TEMPLATE_MAPPING.items()
}

WIDGET_MAPPING: dict[str, str] = {
    "Title": "title",
    "Order": "order",
    "Type": "type",
    "HtmlContent": "html_content",
    "Creator": "creator",
    "Description": "description",
    "Identifier": "identifier",
    "SystemWidgetIdentifier": "system_widget_identifier",
}
WIDGET_MAPPING_REV: dict[str, str] = {v: k for k, v in WIDGET_MAPPING.items()}
WIDGET_HANDLED_KEYS: set[str] = set(WIDGET_MAPPING.keys()) | {"WidgetSize"}
WIDGET_HANDLED_NB_KEYS: set[str] = set(WIDGET_MAPPING_REV.keys()) | {"size"}


def _get_cased(d: SingleJson, camel: str, pascal: str, default: Any = None) -> Any:
    """Retrieve value checking camelCase then PascalCase, preserving valid falsy values."""
    val = d.get(camel)
    if val is not None:
        return val
    val = d.get(pascal)
    if val is not None:
        return val
    return default


def sanitize_step_filename(filename: str, step_id: str | None = None) -> str:
    """Sanitize step name to generate a safe YAML filename.

    Args:
        filename: Raw step name.
        step_id: Optional step identifier for disambiguation.

    Returns:
        Sanitized lowercase filename string.
    """
    filename = filename.replace(" ", "_")
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "", filename)
    if step_id:
        return (sanitized + "_" + step_id[:5]).lower()
    return sanitized.lower()


def _to_snake(key: str) -> str:
    """Convert camelCase or PascalCase string to snake_case."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()


def _to_camel(key: str) -> str:
    """Convert snake_case string to camelCase."""
    parts = key.split("_")
    return parts[0] + "".join(x.title() for x in parts[1:])


def _to_pascal(key: str) -> str:
    """Convert snake_case string to PascalCase."""
    return "".join(x.title() for x in key.split("_"))


def _passthrough(
    src: SingleJson,
    dst: SingleJson,
    handled: set[str],
    convert: Callable[[str], str],
) -> None:
    """Copy unhandled keys from src to dst converting key names."""
    for k, v in src.items():
        if k not in handled:
            dst[convert(k)] = v


# Playbook Definition Mapping


def definition_to_non_built(defn: SingleJson) -> SingleJson:
    """Convert a built playbook definition dict to non-built YAML structure.

    Args:
        defn: Built playbook definition dictionary.

    Returns:
        Non-built playbook definition dictionary.
    """
    non_built: SingleJson = {}
    for b_key, nb_key in DEFINITION_FIELD_MAPPING.items():
        if b_key in defn:
            non_built[nb_key] = defn[b_key]

    if "playbookType" in defn:
        non_built["type"] = PLAYBOOK_TYPE_MAP.get(defn["playbookType"], "playbook")

    _passthrough(defn, non_built, DEFINITION_HANDLED_KEYS, _to_snake)
    return non_built


def non_built_to_definition(nb: SingleJson) -> SingleJson:
    """Convert non-built definition YAML structure back to built definition dictionary.

    Args:
        nb: Non-built definition dictionary.

    Returns:
        Built playbook definition dictionary.
    """
    defn: SingleJson = {}
    for nb_key, b_key in DEFINITION_FIELD_MAPPING_REV.items():
        if nb_key in nb:
            defn[b_key] = nb[nb_key]

    if "type" in nb:
        defn["playbookType"] = PLAYBOOK_TYPE_MAP_REV.get(nb["type"], 0)

    _passthrough(nb, defn, DEFINITION_HANDLED_NB_KEYS, _to_camel)
    return defn


# Trigger Mapping


def trigger_to_non_built(trig: SingleJson) -> SingleJson:
    """Convert built trigger dict to non-built YAML structure.

    Args:
        trig: Built trigger dictionary.

    Returns:
        Non-built trigger dictionary.
    """
    nb: SingleJson = {
        "identifier": trig.get("identifier", ""),
        "is_enabled": trig.get("isEnabled", True),
        "playbook_id": trig.get("definitionIdentifier", ""),
        "playbook_name": trig.get("workflowName", ""),
        "environments": trig.get("environments", []),
    }
    t_type = _get_cased(trig, "type", "Type")
    if t_type is not None:
        nb["type_"] = TRIGGER_TYPE_MAP.get(t_type, "all")

    op = _get_cased(trig, "logicalOperator", "LogicalOperator")
    if op is not None:
        nb["logical_operator"] = LOGICAL_OPERATOR_MAP.get(op, "and")

    conds = _get_cased(trig, "conditions", "Conditions")
    nb_conds: list[SingleJson] = []
    if conds:
        for c in conds:
            match_type_raw = _get_cased(c, "matchType", "MatchType")
            nb_conds.append(
                {
                    "field_name": _get_cased(c, "fieldName", "FieldName"),
                    "value": _get_cased(c, "value", "Value"),
                    "match_type": MATCH_TYPE_MAP.get(match_type_raw, "equal"),
                    "custom_operator_name": _get_cased(
                        c, "customOperatorName", "CustomOperatorName"
                    ),
                }
            )
    nb["conditions"] = nb_conds
    _passthrough(trig, nb, TRIGGER_HANDLED_KEYS, _to_snake)
    return nb


def non_built_to_trigger(nb: SingleJson) -> SingleJson:
    """Convert non-built trigger YAML structure back to built trigger dict.

    Args:
        nb: Non-built trigger dictionary.

    Returns:
        Built trigger dictionary.
    """
    trig: SingleJson = {
        "id": 0,
        "identifier": nb.get("identifier", ""),
        "isEnabled": nb.get("is_enabled", True),
        "definitionIdentifier": nb.get("playbook_id", ""),
        "workflowName": nb.get("playbook_name", ""),
        "environments": nb.get("environments", []),
    }
    if "type_" in nb:
        trig["type"] = TRIGGER_TYPE_MAP_REV.get(nb["type_"], 8)
    if "logical_operator" in nb:
        trig["logicalOperator"] = LOGICAL_OPERATOR_MAP_REV.get(
            nb["logical_operator"], 0
        )

    b_conds: list[SingleJson] = []
    for c in nb.get("conditions", []):
        if c:
            b_conds.append(
                {
                    "fieldName": c.get("field_name"),
                    "value": c.get("value"),
                    "matchType": MATCH_TYPE_MAP_REV.get(c.get("match_type"), 0),
                    "customOperatorName": c.get("custom_operator_name"),
                }
            )
    trig["conditions"] = b_conds
    _passthrough(nb, trig, TRIGGER_HANDLED_NB_KEYS, _to_camel)
    return trig


# Overview Mapping


def overview_to_non_built(ov: SingleJson) -> SingleJson:
    """Convert built overview template dict to non-built YAML structure.

    Args:
        ov: Built overview template dictionary.

    Returns:
        Non-built overview dictionary.
    """
    nb: SingleJson = {}
    template = ov.get("OverviewTemplate", {})
    for b_key, nb_key in OVERVIEW_TEMPLATE_MAPPING.items():
        if b_key in template:
            nb[nb_key] = template[b_key]

    nb["role_names"] = ov.get("Roles", [])
    if "Type" in template:
        nb["type"] = OVERVIEW_TYPE_MAP.get(template["Type"], "regular")

    nb_widgets: list[SingleJson] = []
    for w in template.get("Widgets", []):
        w_dict: SingleJson = {}
        for b_k, nb_k in WIDGET_MAPPING.items():
            if b_k in w:
                w_dict[nb_k] = w[b_k]
        if "WidgetSize" in w:
            w_dict["size"] = WIDGET_SIZE_MAP.get(w.get("WidgetSize"), "medium")
        _passthrough(w, w_dict, WIDGET_HANDLED_KEYS, _to_snake)
        nb_widgets.append(w_dict)
    nb["widgets_details"] = nb_widgets
    return nb


def non_built_to_overview(nb: SingleJson) -> SingleJson:
    """Convert non-built overview YAML structure back to built overview dictionary.

    Args:
        nb: Non-built overview dictionary.

    Returns:
        Built overview dictionary.
    """
    template: SingleJson = {}
    for nb_key, b_key in OVERVIEW_TEMPLATE_MAPPING_REV.items():
        if nb_key in nb:
            template[b_key] = nb[nb_key]

    if "type" in nb:
        template["Type"] = OVERVIEW_TYPE_MAP_REV.get(nb["type"], 1)

    widgets: list[SingleJson] = []
    for w in nb.get("widgets_details", []):
        widget: SingleJson = {
            "Title": w.get("title", ""),
            "WidgetSize": WIDGET_SIZE_MAP_REV.get(w.get("size"), 1),
            "Order": w.get("order", 0),
            "Type": w.get("type", 0),
            "HtmlContent": w.get("html_content", ""),
            "Creator": w.get("creator"),
            "Description": w.get("description", ""),
            "Identifier": w.get("identifier", ""),
            "SystemWidgetIdentifier": w.get("system_widget_identifier", ""),
        }
        _passthrough(w, widget, WIDGET_HANDLED_NB_KEYS, _to_pascal)
        widgets.append(widget)
    template["Widgets"] = widgets
    return {
        "Roles": nb.get("role_names", []),
        "OverviewTemplate": template,
    }


# Step Mapping Helpers


def _step_params_to_non_built(params: list[SingleJson] | None) -> list[SingleJson]:
    """Convert built step parameters to non-built YAML structure."""
    if not params:
        return []
    nb_params: list[SingleJson] = []
    for p in params:
        nb_params.append(
            {
                "step_id": _get_cased(p, "stepIdentifier", "StepIdentifier"),
                "playbook_id": _get_cased(
                    p, "workflowIdentifier", "WorkflowIdentifier"
                ),
                "name": _get_cased(p, "name", "Name"),
                "value": _get_cased(p, "value", "Value"),
            }
        )
    return nb_params


def _non_built_to_step_params(
    nb_params: list[SingleJson],
) -> list[SingleJson]:
    """Convert non-built step parameters to built parameters list."""
    b_params: list[SingleJson] = []
    for p in nb_params:
        b_params.append(
            {
                "stepIdentifier": p.get("step_id"),
                "workflowIdentifier": p.get("playbook_id"),
                "name": p.get("name"),
                "value": p.get("value"),
            }
        )
    return b_params


def _step_debug_data_to_non_built(sdd: SingleJson | None) -> SingleJson | None:
    """Convert built step debug data to non-built YAML structure."""
    if not sdd:
        return None
    return {
        "step_id": _get_cased(sdd, "originalStepIdentifier", "OriginalStepIdentifier"),
        "playbook_id": _get_cased(
            sdd, "originalWorkflowIdentifier", "OriginalWorkflowIdentifier"
        ),
        "creation_time": _get_cased(
            sdd, "creationTimeUnixTimeInMs", "CreationTimeUnixTimeInMs"
        ),
        "modification_time": _get_cased(
            sdd, "modificationTimeUnixTimeInMs", "ModificationTimeUnixTimeInMs"
        ),
        "result_value": _get_cased(sdd, "resultValue", "ResultValue"),
        "result_json": _get_cased(sdd, "resultJson", "ResultJson"),
        "scope_entities_enrichment_data": _get_cased(
            sdd,
            "scopeEntitiesEnrichmentData",
            "ScopeEntitiesEnrichmentData",
            default=[],
        ),
        "tenant_id": _get_cased(sdd, "tenantId", "TenantId"),
    }


def _non_built_to_step_debug_data(
    sdd: SingleJson | None,
) -> SingleJson | None:
    """Convert non-built step debug data to built structure."""
    if not sdd:
        return None
    scope_data = sdd.get("scope_entities_enrichment_data", [])
    return {
        "originalStepIdentifier": sdd.get("step_id"),
        "originalWorkflowIdentifier": sdd.get("playbook_id"),
        "creationTimeUnixTimeInMs": sdd.get("creation_time"),
        "modificationTimeUnixTimeInMs": sdd.get("modification_time"),
        "resultValue": sdd.get("result_value"),
        "resultJson": sdd.get("result_json"),
        "scopeEntitiesEnrichmentData": scope_data,
        "scopeEntitiesEnrichmentDataJson": json.dumps(scope_data),
        "tenantId": sdd.get("tenant_id"),
    }


def step_to_non_built(step: SingleJson) -> SingleJson:
    """Convert built step dict to non-built YAML structure.

    Args:
        step: Built step dictionary.

    Returns:
        Non-built step dictionary.
    """
    nb: SingleJson = {}
    for nb_key, camel_key in STEP_FIELD_MAPPING.items():
        pascal_key = camel_key[0].upper() + camel_key[1:]
        val = _get_cased(step, camel_key, pascal_key)
        if val is not None:
            nb[nb_key] = val

    s_type = _get_cased(step, "type", "Type")
    if s_type is not None:
        nb["type"] = STEP_TYPE_MAP.get(s_type, "action")

    nb["parameters"] = _step_params_to_non_built(
        _get_cased(step, "parameters", "Parameters")
    )

    pa_list = _get_cased(step, "parallelActions", "ParallelActions")
    nb["parallel_actions"] = (
        [step_to_non_built(pa) for pa in pa_list] if pa_list else []
    )

    nb["step_debug_data"] = _step_debug_data_to_non_built(
        _get_cased(step, "stepDebugData", "StepDebugData")
    )
    return nb


def non_built_to_step(nb: SingleJson) -> SingleJson:
    """Convert non-built step YAML structure back to built step dict.

    Args:
        nb: Non-built step dictionary.

    Returns:
        Built step dictionary.
    """
    step: SingleJson = {}
    for nb_key, camel_key in STEP_FIELD_MAPPING.items():
        if nb_key in nb:
            step[camel_key] = nb[nb_key]

    if "type" in nb:
        step["type"] = STEP_TYPE_MAP_REV.get(nb["type"], 0)

    step["parameters"] = _non_built_to_step_params(nb.get("parameters", []))
    step["parallelActions"] = [
        non_built_to_step(pa) for pa in nb.get("parallel_actions", [])
    ]
    step["stepDebugData"] = _non_built_to_step_debug_data(nb.get("step_debug_data"))

    if "playbook_id" in nb:
        step["workflowIdentifier"] = nb["playbook_id"]

    # Only used to rebuild stepsRelations; not a platform step field.
    step.pop("destinationActionStatuses", None)
    return step


# Deconstruct and Reconstruct Orchestrators


def _build_parent_maps(
    relations: list[SingleJson],
) -> tuple[
    dict[str, list[str]],
    dict[str, dict[str, str]],
    dict[str, dict[str, int]],
]:
    """Build parent step mappings, conditions, and action statuses from relations."""
    parents_map: dict[str, list[str]] = {}
    conditions_map: dict[str, dict[str, str]] = {}
    dest_status_map: dict[str, dict[str, int]] = {}
    for rel in relations:
        from_step = rel.get("fromStep")
        to_step = rel.get("toStep")
        cond = rel.get("condition") or ""
        status = rel.get("destinationActionStatus", 0)
        if from_step and to_step:
            parents_map.setdefault(to_step, []).append(from_step)
            conditions_map.setdefault(to_step, {})[from_step] = cond
            dest_status_map.setdefault(to_step, {})[from_step] = status
    return parents_map, conditions_map, dest_status_map


def _inject_step_relations(
    steps: list[SingleJson], relations: list[SingleJson]
) -> list[SingleJson]:
    """Inject parent relation metadata into shallow-copied steps without mutating originals."""
    parents_map, conditions_map, dest_status_map = _build_parent_maps(relations)
    copied_steps: list[SingleJson] = []
    for s in steps:
        step_copy = dict(s)
        step_id = step_copy.get("identifier") or step_copy.get("Identifier")
        if step_id:
            if (
                "parentStepIdentifiers" not in step_copy
                and "ParentStepIdentifiers" not in step_copy
            ):
                step_copy["parentStepIdentifiers"] = parents_map.get(step_id, [])
            if (
                "parentStepIdentifier" not in step_copy
                and "ParentStepIdentifier" not in step_copy
            ):
                p_list = parents_map.get(step_id, [])
                step_copy["parentStepIdentifier"] = p_list[0] if p_list else ""
            if (
                "previousResultCondition" not in step_copy
                and "PreviousResultCondition" not in step_copy
            ):
                conds = conditions_map.get(step_id, {})
                step_copy["previousResultCondition"] = json.dumps(conds)
            if (
                "destinationActionStatuses" not in step_copy
                and "DestinationActionStatuses" not in step_copy
            ):
                statuses = dest_status_map.get(step_id, {})
                if any(v != 0 for v in statuses.values()):
                    step_copy["destinationActionStatuses"] = json.dumps(statuses)
        copied_steps.append(step_copy)
    return copied_steps


def _build_display_info(
    playbook_dict: SingleJson, existing_files: dict[str, bytes]
) -> SingleJson:
    """Build display_info content dictionary."""
    existing_display: SingleJson = {}
    if "display_info.yaml" in existing_files:
        try:
            parsed = yaml.safe_load(existing_files["display_info.yaml"])
            if isinstance(parsed, dict):
                existing_display = parsed
        except yaml.YAMLError as e:
            LOGGER.warning(f"Failed to parse display_info.yaml: {e}")

    return {
        "type": (
            "block"
            if str(playbook_dict.get("playbookType")) in ("1", "block")
            else "playbook"
        ),
        "content_hub_display_name": playbook_dict.get("name", ""),
        "author": existing_display.get("author") or "",
        "contact_email": existing_display.get("contact_email") or "",
        "tags": existing_display.get("tags")
        or [playbook_dict.get("categoryName", "Default")],
        "should_display_in_content_hub": existing_display.get(
            "should_display_in_content_hub", True
        ),
        "contribution_type": existing_display.get("contribution_type") or "third_party",
        "acknowledge_debug_data_included": existing_display.get(
            "acknowledge_debug_data_included", False
        ),
    }


def _build_release_notes(
    playbook_dict: SingleJson, existing_files: dict[str, bytes]
) -> list[SingleJson]:
    """Build release_notes content list."""
    existing_rn: list[SingleJson] = []
    if "release_notes.yaml" in existing_files:
        try:
            parsed = yaml.safe_load(existing_files["release_notes.yaml"])
            if isinstance(parsed, list):
                existing_rn = parsed
        except yaml.YAMLError as e:
            LOGGER.warning(f"Failed to parse release_notes.yaml: {e}")

    if not existing_rn:
        existing_rn = [
            {
                "description": playbook_dict.get("description")
                or "Initial playbook release.",
                "version": playbook_dict.get("version") or 1.0,
                "item_name": playbook_dict.get("name"),
                "item_type": (
                    "Block"
                    if str(playbook_dict.get("playbookType")) in ("1", "block")
                    else "Playbook"
                ),
                "publish_time": int(
                    (playbook_dict.get("modificationTimeUnixTimeInMs") or 0) / 1000
                ),
                "ticket_number": "",
            }
        ]
    return existing_rn


def _reconstruct_step_relations(
    nb_step: SingleJson, step_obj: SingleJson
) -> list[SingleJson]:
    """Reconstruct step relations for a single non-built step."""
    parent_ids = list(nb_step.get("parent_step_ids") or [])
    parent_id = nb_step.get("parent_step_id")
    if parent_id and parent_id not in parent_ids:
        parent_ids.append(parent_id)

    prev_cond_str = nb_step.get("previous_result_condition") or "{}"
    try:
        prev_cond = (
            json.loads(prev_cond_str)
            if isinstance(prev_cond_str, str)
            else prev_cond_str
        )
    except (json.JSONDecodeError, TypeError):
        prev_cond = {}

    status_map_str = nb_step.get("destination_action_statuses") or "{}"
    try:
        status_map = (
            json.loads(status_map_str)
            if isinstance(status_map_str, str)
            else status_map_str
        )
    except (json.JSONDecodeError, TypeError):
        status_map = {}

    to_step_id = step_obj.get("identifier") or step_obj.get("Identifier")
    relations: list[SingleJson] = []
    for p_id in parent_ids:
        if p_id:
            cond_val = prev_cond.get(p_id, "") if isinstance(prev_cond, dict) else ""
            status_val = status_map.get(p_id, 0) if isinstance(status_map, dict) else 0
            relations.append(
                {
                    "condition": str(cond_val),
                    "fromStep": p_id,
                    "toStep": to_step_id,
                    "destinationActionStatus": (
                        int(status_val)
                        if isinstance(status_val, int)
                        or (isinstance(status_val, str) and status_val.isdigit())
                        else 0
                    ),
                }
            )
    return relations


def _yaml_file(path: str, data: JSON) -> File:
    """Helper to serialize data to a YAML File object."""
    return File(path, yaml.safe_dump(data, indent=4, sort_keys=False))


def _build_trigger_data(playbook_dict: SingleJson) -> SingleJson:
    """Build non-built trigger data dictionary."""
    trigger = playbook_dict.get("trigger")
    if trigger:
        return trigger_to_non_built(trigger)
    return {
        "identifier": "",
        "is_enabled": True,
        "playbook_id": playbook_dict.get("identifier", ""),
        "type_": "all",
        "conditions": [],
        "logical_operator": "and",
        "environments": ["*"],
    }


def _build_step_files(steps: list[SingleJson]) -> list[File]:
    """Build list of File objects for deconstructed steps."""
    step_files: list[File] = []
    for s in steps:
        non_built_s = step_to_non_built(s)
        step_name = s.get("instanceName") or s.get("name") or s.get("Name") or ""
        step_id = s.get("identifier") or s.get("Identifier")
        filename = f"steps/{sanitize_step_filename(step_name, step_id)}.yaml"
        step_files.append(_yaml_file(filename, non_built_s))
    return step_files


def _reconstruct_steps(
    files_dict: dict[str, bytes],
) -> tuple[list[SingleJson], list[SingleJson]]:
    """Parse and reconstruct steps and step relations from deconstructed files."""
    steps: list[SingleJson] = []
    steps_relations: list[SingleJson] = []
    for filename, content in files_dict.items():
        if filename.startswith("steps/") and filename.endswith(".yaml"):
            nb_step = yaml.safe_load(content.decode("utf-8")) or {}
            step_obj = non_built_to_step(nb_step)
            steps.append(step_obj)
            steps_relations.extend(_reconstruct_step_relations(nb_step, step_obj))
    return steps, steps_relations


class PlaybookYAMLConverter:
    """Converter for deconstructing and reconstructing playbooks to and from modular YAML."""

    @staticmethod
    def deconstruct_playbook(
        playbook_dict: SingleJson,
        existing_files: dict[str, bytes] | None = None,
    ) -> list[File]:
        """Convert a built playbook dict into deconstructed YAML File objects.

        If existing_files is provided, parses metadata fields (e.g. from display_info.yaml
        or release_notes.yaml) to preserve details like authors and version notes.

        Args:
            playbook_dict: Raw built playbook dictionary.
            existing_files: Optional existing files map from repository.

        Returns:
            List of File objects containing the deconstructed YAML files.
        """
        existing_files = existing_files or {}
        relations = playbook_dict.get("stepsRelations") or []
        steps = _inject_step_relations(playbook_dict.get("steps", []), relations)

        overviews = playbook_dict.get("OverviewTemplatesDetails", [])
        nb_overviews = [overview_to_non_built(ov) for ov in overviews]

        files = [
            _yaml_file("definition.yaml", definition_to_non_built(playbook_dict)),
            _yaml_file("trigger.yaml", _build_trigger_data(playbook_dict)),
            _yaml_file(
                "display_info.yaml",
                _build_display_info(playbook_dict, existing_files),
            ),
            _yaml_file("overviews.yaml", nb_overviews),
            _yaml_file(
                "release_notes.yaml",
                _build_release_notes(playbook_dict, existing_files),
            ),
        ]
        files.extend(_build_step_files(steps))
        return files

    @staticmethod
    def reconstruct_playbook(files_dict: dict[str, bytes]) -> SingleJson:
        """Convert deconstructed YAML files back into a built playbook JSON dictionary.

        Args:
            files_dict: Map of relative filenames to file contents in bytes.

        Returns:
            Built playbook dictionary.
        """
        nb_meta = (
            yaml.safe_load(files_dict.get("definition.yaml", b"{}").decode("utf-8"))
            or {}
        )
        playbook = non_built_to_definition(nb_meta)

        if "trigger.yaml" in files_dict:
            nb_trig = yaml.safe_load(files_dict["trigger.yaml"].decode("utf-8")) or {}
            playbook["trigger"] = non_built_to_trigger(nb_trig)
        else:
            playbook["trigger"] = None

        overviews_details: list[SingleJson] = []
        if "overviews.yaml" in files_dict:
            nb_overviews = (
                yaml.safe_load(files_dict["overviews.yaml"].decode("utf-8")) or []
            )
            overviews_details = [non_built_to_overview(ov) for ov in nb_overviews]
        playbook["OverviewTemplatesDetails"] = overviews_details
        playbook["WidgetTemplates"] = []

        steps, steps_relations = _reconstruct_steps(files_dict)
        playbook["steps"] = steps
        playbook["stepsRelations"] = steps_relations
        playbook["id"] = 0
        return playbook
