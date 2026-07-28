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
import re
import yaml
from .definitions import File

# Enum/Integer mappings for Playbooks

PLAYBOOK_TYPE_MAP = {
    0: "playbook",
    1: "block",
}
PLAYBOOK_TYPE_MAP_REV = {v: k for k, v in PLAYBOOK_TYPE_MAP.items()}

CREATION_SOURCE_MAP = {
    0: "playbook_creation_source_unspecified",
    1: "user_or_api_initiated",
    2: "ai_generated_from_alert",
    3: "ai_generated_from_prompt",
}
CREATION_SOURCE_MAP_REV = {v: k for k, v in CREATION_SOURCE_MAP.items()}

ACCESS_LEVEL_MAP = {
    0: "no_access",
    1: "view",
    2: "edit",
}
ACCESS_LEVEL_MAP_REV = {v: k for k, v in ACCESS_LEVEL_MAP.items()}

TRIGGER_TYPE_MAP = {
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
TRIGGER_TYPE_MAP_REV = {v: k for k, v in TRIGGER_TYPE_MAP.items()}

LOGICAL_OPERATOR_MAP = {
    0: "and",
    1: "or",
}
LOGICAL_OPERATOR_MAP_REV = {v: k for k, v in LOGICAL_OPERATOR_MAP.items()}

MATCH_TYPE_MAP = {
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
MATCH_TYPE_MAP_REV = {v: k for k, v in MATCH_TYPE_MAP.items()}

STEP_TYPE_MAP = {
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
STEP_TYPE_MAP_REV = {v: k for k, v in STEP_TYPE_MAP.items()}


def sanitize_step_filename(filename: str, step_id: str | None = None) -> str:
    filename = filename.replace(" ", "_")
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "", filename)
    if step_id:
        return (sanitized + "_" + step_id[:5]).lower()
    return sanitized.lower()


# Playbook Definition Mapping

def definition_to_non_built(defn: dict) -> dict:
    non_built = {}
    mapping = {
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
    
    for b_key, nb_key in mapping.items():
        if b_key in defn:
            non_built[nb_key] = defn[b_key]
            
    if "playbookType" in defn:
        non_built["type"] = PLAYBOOK_TYPE_MAP.get(defn["playbookType"], "playbook")

    mapped_keys = set(mapping.keys()) | {"playbookType", "trigger", "steps", "stepsRelations", "id"}
    for k, v in defn.items():
        if k not in mapped_keys:
            snake_k = re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
            non_built[snake_k] = v
        
    return non_built


def non_built_to_definition(nb: dict) -> dict:
    defn = {}
    mapping = {
        "identifier": "identifier",
        "is_enable": "isEnabled",
        "version": "version",
        "name": "name",
        "description": "description",
        "priority": "priority",
        "category_name": "categoryName",
        "category": "categoryId",
        "environments": "environments",
        "is_debug_mode": "isDebugMode",
        "simulation_clone": "simulationClone",
    }
    
    for nb_key, b_key in mapping.items():
        if nb_key in nb:
            defn[b_key] = nb[nb_key]
            
    if "type" in nb:
        defn["playbookType"] = PLAYBOOK_TYPE_MAP_REV.get(nb["type"], 0)

    mapped_nb_keys = set(mapping.keys()) | {"type"}
    for k, v in nb.items():
        if k not in mapped_nb_keys:
            parts = k.split('_')
            camel_k = parts[0] + ''.join(x.title() for x in parts[1:])
            defn[camel_k] = v
        
    return defn


# Trigger Mapping

def trigger_to_non_built(trig: dict) -> dict:
    nb = {}
    mapping = {
        "identifier": "identifier",
        "isEnabled": "is_enabled",
        "definitionIdentifier": "playbook_id",
        "workflowName": "playbook_name",
        "environments": "environments",
    }
    for b_key, nb_key in mapping.items():
        if b_key in trig:
            nb[nb_key] = trig[b_key]
            
    t_type = trig.get("type") if trig.get("type") is not None else trig.get("Type")
    if t_type is not None:
        nb["type_"] = TRIGGER_TYPE_MAP.get(t_type, "all")
        
    op = trig.get("logicalOperator") if trig.get("logicalOperator") is not None else trig.get("LogicalOperator")
    if op is not None:
        nb["logical_operator"] = LOGICAL_OPERATOR_MAP.get(op, "and")
        
    conds = trig.get("conditions") if trig.get("conditions") is not None else trig.get("Conditions")
    if conds:
        nb_conds = []
        for c in conds:
            nb_conds.append({
                "field_name": c.get("fieldName") or c.get("FieldName"),
                "value": c.get("value") or c.get("Value"),
                "match_type": MATCH_TYPE_MAP.get(c.get("matchType") if c.get("matchType") is not None else c.get("MatchType"), "equal"),
                "custom_operator_name": c.get("customOperatorName") or c.get("CustomOperatorName")
            })
        nb["conditions"] = nb_conds
    else:
        nb["conditions"] = []
        
    return nb


def non_built_to_trigger(nb: dict, is_1p: bool = False) -> dict:
    trig = {
        "id": 0
    }
    mapping = {
        "identifier": "identifier",
        "is_enabled": "isEnabled",
        "playbook_id": "definitionIdentifier",
        "playbook_name": "workflowName",
        "environments": "environments",
    }
    for nb_key, b_key in mapping.items():
        if nb_key in nb:
            trig[b_key] = nb[nb_key]
            
    if "type_" in nb:
        val = TRIGGER_TYPE_MAP_REV.get(nb["type_"], 8)
        if is_1p:
            trig["Type"] = val
        else:
            trig["type"] = val
    if "logical_operator" in nb:
        val = LOGICAL_OPERATOR_MAP_REV.get(nb["logical_operator"], 0)
        if is_1p:
            trig["LogicalOperator"] = val
        else:
            trig["logicalOperator"] = val
        
    if "conditions" in nb:
        b_conds = []
        for c in nb["conditions"]:
            if c:
                cond_dict = {}
                if is_1p:
                    cond_dict["FieldName"] = c.get("field_name")
                    cond_dict["Value"] = c.get("value")
                    cond_dict["MatchType"] = MATCH_TYPE_MAP_REV.get(c.get("match_type"), 0)
                    cond_dict["CustomOperatorName"] = c.get("custom_operator_name")
                else:
                    cond_dict["fieldName"] = c.get("field_name")
                    cond_dict["value"] = c.get("value")
                    cond_dict["matchType"] = MATCH_TYPE_MAP_REV.get(c.get("match_type"), 0)
                    cond_dict["customOperatorName"] = c.get("custom_operator_name")
                b_conds.append(cond_dict)
        if is_1p:
            trig["Conditions"] = b_conds
        else:
            trig["conditions"] = b_conds
    else:
        if is_1p:
            trig["Conditions"] = []
        else:
            trig["conditions"] = []
        
    return trig


# Overview Mapping

def overview_to_non_built(ov: dict) -> dict:
    nb = {}
    template = ov.get("OverviewTemplate", {})
    mapping = {
        "Identifier": "identifier",
        "Name": "name",
        "Creator": "creator",
        "PlaybookDefinitionIdentifier": "playbook_id",
        "AlertRuleType": "alert_rule_type",
        "Roles": "roles",
    }
    for b_key, nb_key in mapping.items():
        if b_key in template:
            nb[nb_key] = template[b_key]
            
    nb["role_names"] = ov.get("Roles", [])
    if "Type" in template:
        nb["type"] = {0: "playbook_default", 1: "regular", 2: "system_alert", 3: "system_case", 4: "alert_type"}.get(template["Type"], "regular")
        
    nb_widgets = []
    for w in template.get("Widgets", []):
        nb_widgets.append({
            "title": w.get("Title"),
            "size": {0: "small", 1: "medium", 2: "large"}.get(w.get("WidgetSize"), "medium"),
            "order": w.get("Order")
        })
    nb["widgets_details"] = nb_widgets
    return nb


def non_built_to_overview(nb: dict) -> dict:
    ov = {}
    template = {}
    mapping = {
        "identifier": "Identifier",
        "name": "Name",
        "creator": "Creator",
        "playbook_id": "PlaybookDefinitionIdentifier",
        "alert_rule_type": "AlertRuleType",
        "roles": "Roles",
    }
    for nb_key, b_key in mapping.items():
        if nb_key in nb:
            template[b_key] = nb[nb_key]
            
    ov["Roles"] = nb.get("role_names", [])
    if "type" in nb:
        template["Type"] = {"playbook_default": 0, "regular": 1, "system_alert": 2, "system_case": 3, "alert_type": 4}.get(nb["type"], 1)
        
    widgets = []
    for w in nb.get("widgets_details", []):
        widgets.append({
            "Title": w.get("title"),
            "WidgetSize": {"small": 0, "medium": 1, "large": 2}.get(w.get("size"), 1),
            "Order": w.get("order"),
            "Type": 0,
            "HtmlContent": "",
            "Creator": None,
            "Description": "",
            "Identifier": "",
            "SystemWidgetIdentifier": ""
        })
    template["Widgets"] = widgets
    ov["OverviewTemplate"] = template
    return ov


# Step Mapping

def step_to_non_built(step: dict) -> dict:
    nb = {}
    mapping = {
        "identifier": "identifier",
        "Identifier": "identifier",
        "originalStepIdentifier": "original_step_id",
        "OriginalStepIdentifier": "original_step_id",
        "parentWorkflowIdentifier": "playbook_id",
        "ParentWorkflowIdentifier": "playbook_id",
        "parentStepIdentifiers": "parent_step_ids",
        "ParentStepIdentifiers": "parent_step_ids",
        "parentStepIdentifier": "parent_step_id",
        "ParentStepIdentifier": "parent_step_id",
        "previousResultCondition": "previous_result_condition",
        "PreviousResultCondition": "previous_result_condition",
        "instanceName": "instance_name",
        "InstanceName": "instance_name",
        "isAutomatic": "is_automatic",
        "IsAutomatic": "is_automatic",
        "name": "name",
        "Name": "name",
        "isSkippable": "is_skippable",
        "IsSkippable": "is_skippable",
        "description": "description",
        "Description": "description",
        "actionProvider": "action_provider",
        "ActionProvider": "action_provider",
        "actionName": "action_name",
        "ActionName": "action_name",
        "integration": "integration",
        "Integration": "integration",
        "autoSkipOnFailure": "auto_skip_on_failure",
        "AutoSkipOnFailure": "auto_skip_on_failure",
        "isDebugMockData": "is_debug_mock_data",
        "IsDebugMockData": "is_debug_mock_data",
        "parentStepContainerId": "parent_container_id",
        "ParentStepContainerId": "parent_container_id",
        "isTouchedByAi": "is_touched_by_ai",
        "IsTouchedByAi": "is_touched_by_ai",
        "startLoopStepIdentifier": "start_loop_step_id",
        "StartLoopStepIdentifier": "start_loop_step_id",
    }
    for b_key, nb_key in mapping.items():
        if b_key in step:
            nb[nb_key] = step[b_key]
            
    s_type = step.get("type") if step.get("type") is not None else step.get("Type")
    if s_type is not None:
        nb["type"] = STEP_TYPE_MAP.get(s_type, "action")
        
    params = step.get("parameters") if step.get("parameters") is not None else step.get("Parameters")
    if params:
        nb_params = []
        for p in params:
            nb_params.append({
                "step_id": p.get("stepIdentifier") or p.get("StepIdentifier"),
                "playbook_id": p.get("workflowIdentifier") or p.get("WorkflowIdentifier"),
                "name": p.get("name") or p.get("Name"),
                "value": p.get("value") or p.get("Value")
            })
        nb["parameters"] = nb_params
    else:
        nb["parameters"] = []
        
    pa_list = step.get("parallelActions") if step.get("parallelActions") is not None else step.get("ParallelActions")
    if pa_list:
        nb["parallel_actions"] = [step_to_non_built(pa) for pa in pa_list]
    else:
        nb["parallel_actions"] = []
        
    sdd = step.get("stepDebugData") if step.get("stepDebugData") is not None else step.get("StepDebugData")
    if sdd:
        nb["step_debug_data"] = {
            "step_id": sdd.get("originalStepIdentifier") or sdd.get("OriginalStepIdentifier"),
            "playbook_id": sdd.get("originalWorkflowIdentifier") or sdd.get("OriginalWorkflowIdentifier"),
            "creation_time": sdd.get("creationTimeUnixTimeInMs") or sdd.get("CreationTimeUnixTimeInMs"),
            "modification_time": sdd.get("modificationTimeUnixTimeInMs") or sdd.get("ModificationTimeUnixTimeInMs"),
            "result_value": sdd.get("resultValue") or sdd.get("ResultValue"),
            "result_json": sdd.get("resultJson") or sdd.get("ResultJson"),
            "scope_entities_enrichment_data": sdd.get("scopeEntitiesEnrichmentData") or sdd.get("ScopeEntitiesEnrichmentData", []),
            "tenant_id": sdd.get("tenantId") or sdd.get("TenantId")
        }
    else:
        nb["step_debug_data"] = None
        
    return nb


def non_built_to_step(nb: dict, is_1p: bool = False) -> dict:
    step = {}
    mapping = {
        "identifier": "identifier",
        "original_step_id": "originalStepIdentifier",
        "playbook_id": "parentWorkflowIdentifier",
        "parent_step_ids": "parentStepIdentifiers",
        "parent_step_id": "parentStepIdentifier",
        "previous_result_condition": "previousResultCondition",
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
    for nb_key, b_key in mapping.items():
        if nb_key in nb:
            if is_1p:
                pascal_key = b_key[0].upper() + b_key[1:]
                step[pascal_key] = nb[nb_key]
            else:
                step[b_key] = nb[nb_key]
            
    if "type" in nb:
        val = STEP_TYPE_MAP_REV.get(nb["type"], 0)
        if is_1p:
            step["Type"] = val
        else:
            step["type"] = val
        
    if "parameters" in nb:
        b_params = []
        for p in nb["parameters"]:
            param_dict = {}
            if is_1p:
                param_dict["StepIdentifier"] = p.get("step_id")
                param_dict["WorkflowIdentifier"] = p.get("playbook_id")
                param_dict["Name"] = p.get("name")
                param_dict["Value"] = p.get("value")
            else:
                param_dict["stepIdentifier"] = p.get("step_id")
                param_dict["workflowIdentifier"] = p.get("playbook_id")
                param_dict["name"] = p.get("name")
                param_dict["value"] = p.get("value")
            b_params.append(param_dict)
        if is_1p:
            step["Parameters"] = b_params
        else:
            step["parameters"] = b_params
    else:
        if is_1p:
            step["Parameters"] = []
        else:
            step["parameters"] = []
        
    if "parallel_actions" in nb:
        p_acts = [non_built_to_step(pa, is_1p=is_1p) for pa in nb["parallel_actions"]]
        if is_1p:
            step["ParallelActions"] = p_acts
        else:
            step["parallelActions"] = p_acts
    else:
        if is_1p:
            step["ParallelActions"] = []
        else:
            step["parallelActions"] = []
        
    if "step_debug_data" in nb and nb["step_debug_data"]:
        sdd = nb["step_debug_data"]
        sdd_val = {}
        if is_1p:
            sdd_val["OriginalStepIdentifier"] = sdd.get("step_id")
            sdd_val["OriginalWorkflowIdentifier"] = sdd.get("playbook_id")
            sdd_val["CreationTimeUnixTimeInMs"] = sdd.get("creation_time")
            sdd_val["ModificationTimeUnixTimeInMs"] = sdd.get("modification_time")
            sdd_val["ResultValue"] = sdd.get("result_value")
            sdd_val["ResultJson"] = sdd.get("result_json")
            sdd_val["ScopeEntitiesEnrichmentData"] = sdd.get("scope_entities_enrichment_data", [])
            sdd_val["ScopeEntitiesEnrichmentDataJson"] = json.dumps(sdd.get("scope_entities_enrichment_data", []))
            sdd_val["TenantId"] = sdd.get("tenant_id")
        else:
            sdd_val["originalStepIdentifier"] = sdd.get("step_id")
            sdd_val["originalWorkflowIdentifier"] = sdd.get("playbook_id")
            sdd_val["creationTimeUnixTimeInMs"] = sdd.get("creation_time")
            sdd_val["modificationTimeUnixTimeInMs"] = sdd.get("modification_time")
            sdd_val["resultValue"] = sdd.get("result_value")
            sdd_val["resultJson"] = sdd.get("result_json")
            sdd_val["scopeEntitiesEnrichmentData"] = sdd.get("scope_entities_enrichment_data", [])
            sdd_val["scopeEntitiesEnrichmentDataJson"] = json.dumps(sdd.get("scope_entities_enrichment_data", []))
            sdd_val["tenantId"] = sdd.get("tenant_id")
        if is_1p:
            step["StepDebugData"] = sdd_val
        else:
            step["stepDebugData"] = sdd_val
    else:
        if is_1p:
            step["StepDebugData"] = None
        else:
            step["stepDebugData"] = None

    # Include workflowIdentifier (camelCase always)
    if "playbook_id" in nb:
        step["workflowIdentifier"] = nb["playbook_id"]
        
    return step


# Deconstruct and Reconstruct Orchestrators

class PlaybookYAMLConverter:
    @staticmethod
    def deconstruct_playbook(playbook_dict: dict, existing_files: dict[str, bytes] | None = None) -> list[File]:
        """Convert a built playbook dict into deconstructed YAML File objects.
        If existing_files is provided, parses metadata fields (e.g. from display_info.yaml
        or release_notes.yaml) to preserve details like authors and version notes.
        """
        existing_files = existing_files or {}
        files = []
        
        # Build parent relations and conditions map from stepsRelations if steps don't have them
        relations = playbook_dict.get("stepsRelations") or []
        parents_map = {}
        conditions_map = {}
        for rel in relations:
            from_step = rel.get("fromStep")
            to_step = rel.get("toStep")
            cond = rel.get("condition") or ""
            if from_step and to_step:
                if to_step not in parents_map:
                    parents_map[to_step] = []
                parents_map[to_step].append(from_step)
                if to_step not in conditions_map:
                    conditions_map[to_step] = {}
                conditions_map[to_step][from_step] = cond
                
        # Inject parent relations into steps if not present
        steps = playbook_dict.get("steps", [])
        for s in steps:
            step_id = s.get("identifier") or s.get("Identifier")
            if step_id:
                if "parentStepIdentifiers" not in s and "ParentStepIdentifiers" not in s:
                    s["parentStepIdentifiers"] = parents_map.get(step_id, [])
                if "parentStepIdentifier" not in s and "ParentStepIdentifier" not in s:
                    p_list = parents_map.get(step_id, [])
                    s["parentStepIdentifier"] = p_list[0] if p_list else ""
                if "previousResultCondition" not in s and "PreviousResultCondition" not in s:
                    conds = conditions_map.get(step_id, {})
                    s["previousResultCondition"] = json.dumps(conds)
                    
        # 1. definition.yaml
        non_built_meta = definition_to_non_built(playbook_dict)
        def_content = yaml.safe_dump(non_built_meta, indent=4, sort_keys=False)
        files.append(File("definition.yaml", def_content))
        
        # 2. trigger.yaml
        trigger = playbook_dict.get("trigger")
        if trigger:
            non_built_trig = trigger_to_non_built(trigger)
        else:
            non_built_trig = {
                "identifier": "",
                "is_enabled": True,
                "playbook_id": playbook_dict.get("identifier", ""),
                "type_": "all",
                "conditions": [],
                "logical_operator": "and",
                "environments": ["*"]
            }
        trig_content = yaml.safe_dump(non_built_trig, indent=4, sort_keys=False)
        files.append(File("trigger.yaml", trig_content))
        
        # 3. display_info.yaml
        existing_display = {}
        if "display_info.yaml" in existing_files:
            try:
                parsed = yaml.safe_load(existing_files["display_info.yaml"])
                if isinstance(parsed, dict):
                    existing_display = parsed
            except Exception:
                pass
                
        display_info = {
            "type": "block" if str(playbook_dict.get("playbookType")) in ("1", "block") else "playbook",
            "content_hub_display_name": playbook_dict.get("name", ""),
            "author": existing_display.get("author") or "",
            "contact_email": existing_display.get("contact_email") or "",
            "tags": existing_display.get("tags") or [playbook_dict.get("categoryName", "Default")],
            "should_display_in_content_hub": existing_display.get("should_display_in_content_hub", True),
            "contribution_type": existing_display.get("contribution_type") or "third_party",
            "acknowledge_debug_data_included": existing_display.get("acknowledge_debug_data_included", False),
        }
        disp_content = yaml.safe_dump(display_info, indent=4, sort_keys=False)
        files.append(File("display_info.yaml", disp_content))
        
        # 4. overviews.yaml
        overviews = playbook_dict.get("OverviewTemplatesDetails", [])
        nb_overviews = [overview_to_non_built(ov) for ov in overviews]
        ov_content = yaml.safe_dump(nb_overviews, indent=4, sort_keys=False)
        files.append(File("overviews.yaml", ov_content))
        
        # 5. release_notes.yaml
        existing_rn = []
        if "release_notes.yaml" in existing_files:
            try:
                existing_rn = yaml.safe_load(existing_files["release_notes.yaml"]) or []
            except Exception:
                pass
        
        if not existing_rn:
            existing_rn = [{
                "description": playbook_dict.get("description") or "Initial playbook release.",
                "version": playbook_dict.get("version") or 1.0,
                "item_name": playbook_dict.get("name"),
                "item_type": "Block" if str(playbook_dict.get("playbookType")) in ("1", "block") else "Playbook",
                "publish_time": int((playbook_dict.get("modificationTimeUnixTimeInMs") or 0) / 1000),
                "ticket_number": ""
            }]
        rn_content = yaml.safe_dump(existing_rn, indent=4, sort_keys=False)
        files.append(File("release_notes.yaml", rn_content))
        
        # 6. steps/*.yaml
        steps = playbook_dict.get("steps", [])
        for s in steps:
            non_built_s = step_to_non_built(s)
            filename = f"steps/{sanitize_step_filename(s.get('instanceName') or s.get('name') or s.get('Name'), s.get('identifier') or s.get('Identifier'))}.yaml"
            step_yaml = yaml.safe_dump(non_built_s, indent=4, sort_keys=False)
            files.append(File(filename, step_yaml))
            
        return files

    @staticmethod
    def reconstruct_playbook(files_dict: dict[str, bytes], is_1p: bool = False) -> dict:
        """Convert deconstructed YAML files back into a built playbook JSON dictionary."""
        # 1. Parse definition.yaml
        nb_meta = yaml.safe_load(files_dict.get("definition.yaml", b"{}").decode("utf-8")) or {}
        playbook = non_built_to_definition(nb_meta)
        
        # 2. Parse trigger.yaml
        if "trigger.yaml" in files_dict:
            nb_trig = yaml.safe_load(files_dict["trigger.yaml"].decode("utf-8")) or {}
            playbook["trigger"] = non_built_to_trigger(nb_trig, is_1p=is_1p)
        else:
            playbook["trigger"] = None
            
        # 3. Parse overviews.yaml
        overviews_details = []
        if "overviews.yaml" in files_dict:
            nb_overviews = yaml.safe_load(files_dict["overviews.yaml"].decode("utf-8")) or []
            overviews_details = [non_built_to_overview(ov) for ov in nb_overviews]
        playbook["OverviewTemplatesDetails"] = overviews_details
        playbook["WidgetTemplates"] = []
        
        # 4. Parse steps/*.yaml
        steps = []
        steps_relations = []
        for filename, content in files_dict.items():
            if filename.startswith("steps/") and filename.endswith(".yaml"):
                nb_step = yaml.safe_load(content.decode("utf-8")) or {}
                step_obj = non_built_to_step(nb_step, is_1p=is_1p)
                steps.append(step_obj)
                
                # Dynamic stepsRelations reconstruction
                parent_ids = nb_step.get("parent_step_ids") or []
                parent_id = nb_step.get("parent_step_id")
                if parent_id and parent_id not in parent_ids:
                    parent_ids = list(parent_ids) + [parent_id]
                    
                prev_cond_str = nb_step.get("previous_result_condition") or "{}"
                try:
                    prev_cond = json.loads(prev_cond_str) if isinstance(prev_cond_str, str) else prev_cond_str
                except Exception:
                    prev_cond = {}
                    
                for p_id in parent_ids:
                    if p_id:
                        cond_val = prev_cond.get(p_id, "") if isinstance(prev_cond, dict) else ""
                        steps_relations.append({
                            "condition": str(cond_val),
                            "fromStep": p_id,
                            "toStep": step_obj.get("Identifier") if is_1p else step_obj.get("identifier"),
                            "destinationActionStatus": 0
                        })
                        
        playbook["steps"] = steps
        playbook["stepsRelations"] = steps_relations
        
        playbook["id"] = 0
        
        return playbook
