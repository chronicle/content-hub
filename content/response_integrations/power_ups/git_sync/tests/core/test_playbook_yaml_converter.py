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

import yaml
from TIPCommon.types import SingleJson

from ...core.definitions import File
from ...core.playbook_yaml_converter import PlaybookYAMLConverter
from ..common import MOCKS_PATH

with open(MOCKS_PATH / "mock_data.json", encoding="utf-8") as f:
    MOCK_DATA = json.load(f)

GIT_PLAYBOOK_DATA = MOCK_DATA["git_playbook"]

SAMPLE_FLAT_PLAYBOOK: SingleJson = {
    "id": 123,
    "identifier": "my-playbook-uuid",
    "name": "My Great Playbook",
    "description": "This is a great playbook description",
    "playbookType": 0,
    "priority": 3,
    "isEnabled": True,
    "categoryName": "Phishing",
    "categoryId": 5,
    "environments": ["*"],
    "modificationTimeUnixTimeInMs": 1729064789000,
    "hasRestrictedEnvironments": False,
    "someCustomField": "customValue",
    "trigger": {
        "id": 99,
        "identifier": "trigger-uuid",
        "isEnabled": True,
        "type": 8,  # all
        "logicalOperator": 0,  # and
        "conditions": [
            {
                "FieldName": "Device",
                "Value": "laptop",
                "MatchType": 0,  # equal
            }
        ],
    },
    "steps": [
        {
            "identifier": "12345678",
            "originalStepIdentifier": "12345678",
            "name": "First Step",
            "instanceName": "First Step Instance",
            "type": 0,  # action
            "actionProvider": "Ping",
            "actionName": "Ping Action",
            "integration": "Ping",
            "parameters": [
                {
                    "StepIdentifier": "12345678",
                    "WorkflowIdentifier": "my-playbook-uuid",
                    "Name": "Host",
                    "Value": "8.8.8.8",
                }
            ],
            "parallelActions": [],
        },
        {
            "identifier": "87654321",
            "originalStepIdentifier": "87654321",
            "name": "Second Step",
            "instanceName": "Second Step Instance",
            "type": 0,
            "actionProvider": "Ping",
            "actionName": "Ping Action",
            "integration": "Ping",
            "parentStepIdentifiers": ["12345678"],
            "parentStepIdentifier": "12345678",
            "previousResultCondition": '{"12345678":"Approve"}',
            "parameters": [],
            "parallelActions": [],
        },
    ],
    "stepsRelations": [
        {
            "condition": "Approve",
            "fromStep": "12345678",
            "toStep": "87654321",
        }
    ],
}

REAL_WORLD_PLAYBOOK_PAYLOAD: SingleJson = {
    "id": 0,
    "identifier": "366d3145-8131-4cd4-be2a-1d402c0fd1a4",
    "version": "0",
    "isEnabled": True,
    "isDebugMode": False,
    "name": "AWS EC2 Containment",
    "creator": "9e1cb0e4-a750-431a-b413-a7f76a8b62d7",
    "modifiedBy": "9e1cb0e4-a750-431a-b413-a7f76a8b62d7",
    "priority": 2,
    "description": (
        "This block allows the playbook to automatically stop EC2 instances that were"
        " identified in the alert as potentially compromised or suspicious, supporting"
        " the containment phase of the incident response process."
    ),
    "executionScope": 0,
    "environments": ["Default Environment"],
    "categoryName": "Content Hub Playbooks",
    "categoryId": 2,
    "originalPlaybookIdentifier": "366d3145-8131-4cd4-be2a-1d402c0fd1a4",
    "modificationTimeUnixTimeInMs": 1782888411652,
    "trigger": {
        "id": 0,
        "identifier": "dd963174-4e1c-4677-b09a-f57b41a08ed1",
        "type": 11,
        "logicalOperator": 0,
        "conditions": [],
        "reactionLogicalOperator": 1,
        "reactionConditions": None,
        "executionMode": 0,
    },
    "steps": [
        {
            "parallelActions": [],
            "identifier": "1a2f7106-1669-438f-a8b9-9e4d0ccfab84",
            "originalStepIdentifier": "49fe495c-53c9-4160-b83f-5c7e79d875d6",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "Output_2",
            "name": "Output",
            "integration": "Flow",
            "description": "",
            "actionProvider": "Flow",
            "actionName": "OutputAction",
            "type": 6,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "4d58e0f3-007b-48c2-85f4-2ea67f75c99e",
            "originalStepIdentifier": "d4116b8b-18a9-4eaa-81f6-4da3f2b4c1ee",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "AWSEC2 Stop Instance",
            "name": "AWSEC2_Stop Instance",
            "integration": "AWSEC2",
            "description": "Stop EC2 Instance",
            "actionProvider": "Scripts",
            "actionName": "AWSEC2_Stop Instance",
            "type": 0,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "5efb0efb-ea0c-4766-b780-07bda664eed5",
            "originalStepIdentifier": "8d4833b9-8d50-4db1-933f-c81554f32861",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "Instance Ids",
            "name": "Functions_String Functions",
            "integration": "Functions",
            "description": "String functions",
            "actionProvider": "Scripts",
            "actionName": "Functions_String Functions",
            "type": 0,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "80493f4c-0c45-4a4f-9ad4-36bc8a6dab84",
            "originalStepIdentifier": "7180cd40-7de2-4234-9b3d-3b5bb8bb4f1a",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "Init Remediation Variable",
            "name": "Condition",
            "integration": "Flow",
            "description": "Condition",
            "actionProvider": "Flow",
            "actionName": "IfFlowCondition",
            "type": 4,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "8ab8d270-dbd6-4a51-9d68-228a1c7fd217",
            "originalStepIdentifier": "8d78ba0f-eddb-4436-a5a3-e22ab9c9177d",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "NO_COMPUTE_INSTANCE_REMEDIATION_SUMMARY",
            "name": "Tools_Set Context Value",
            "integration": "Tools",
            "description": "Set context",
            "actionProvider": "Scripts",
            "actionName": "Tools_Set Context Value",
            "type": 0,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "8bd0316b-a0f7-4f26-be8f-72e5418d91d8",
            "originalStepIdentifier": "a34fbb69-d409-4008-a3a2-e20b75ec5ae6",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "Init Remediation",
            "name": "Tools_Set Context Value",
            "integration": "Tools",
            "description": "Set context",
            "actionProvider": "Scripts",
            "actionName": "Tools_Set Context Value",
            "type": 0,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "a91fd721-7dfd-4c36-94cb-3fd64596cddc",
            "originalStepIdentifier": "e86ac20b-3f67-4d6e-b120-cf20259d7d8b",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "Output_3",
            "name": "Output",
            "integration": "Flow",
            "description": "",
            "actionProvider": "Flow",
            "actionName": "OutputAction",
            "type": 6,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "ab899475-2030-4b42-b72a-3f458fdcd13b",
            "originalStepIdentifier": "1fccc57f-a0cb-45c0-bb7c-14ed55beb78f",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "AWS EC2 Filter",
            "name": "Entity Selection",
            "integration": "Flow",
            "description": "Entity selection",
            "actionProvider": "Flow",
            "actionName": "EntitySelection",
            "type": 0,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "aff01611-87be-4448-bd3e-f7527434fabe",
            "originalStepIdentifier": "83cdb3a3-8351-48a4-8a4d-29b598e33bb6",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "Has EC2 instance and AWS configured?",
            "name": "Condition",
            "integration": "Flow",
            "description": "Condition",
            "actionProvider": "Flow",
            "actionName": "IfFlowCondition",
            "type": 4,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "e08c4150-f2b6-4537-a09b-4b5e2ec4a0e3",
            "originalStepIdentifier": "a2f13355-61bb-43d3-902a-eb29d4addafd",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "Output_1",
            "name": "Output",
            "integration": "Flow",
            "description": "",
            "actionProvider": "Flow",
            "actionName": "OutputAction",
            "type": 6,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "e82b5ab4-d708-4171-9062-e886ac6f71bd",
            "originalStepIdentifier": "222363f5-8a59-48a5-8f78-6944728f8154",
            "isAutomatic": False,
            "isSkippable": False,
            "instanceName": "Stop EC2 Instance?",
            "name": "MultiChoiceQuestion",
            "integration": "Flow",
            "description": "Question",
            "actionProvider": "Flow",
            "actionName": "MultiChoiceQuestion",
            "type": 1,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "ec21b730-635b-42c6-b03c-f1bbb761b875",
            "originalStepIdentifier": "1fbfff0b-4412-40f3-bf12-a5fb7294bd2a",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "Count Ec2",
            "name": "SiemplifyUtilities_Count Entities In Scope",
            "integration": "SiemplifyUtilities",
            "description": "Count entities",
            "actionProvider": "Scripts",
            "actionName": "SiemplifyUtilities_Count Entities In Scope",
            "type": 0,
            "parameters": [],
        },
        {
            "parallelActions": [],
            "identifier": "f93d6cba-cee5-44f3-a9fd-26437b15dc63",
            "originalStepIdentifier": "13f22c36-aafa-45a5-999d-94db2c4c2533",
            "isAutomatic": True,
            "isSkippable": False,
            "instanceName": "COMPUTE_INSTANCE_REMEDIATION_SUMMARY ",
            "name": "Tools_Set Context Value",
            "integration": "Tools",
            "description": "Set context",
            "actionProvider": "Scripts",
            "actionName": "Tools_Set Context Value",
            "type": 0,
            "parameters": [],
        },
    ],
    "stepsRelations": [
        {
            "condition": "",
            "fromStep": "f93d6cba-cee5-44f3-a9fd-26437b15dc63",
            "toStep": "1a2f7106-1669-438f-a8b9-9e4d0ccfab84",
            "destinationActionStatus": 0,
        },
        {
            "condition": "",
            "fromStep": "5efb0efb-ea0c-4766-b780-07bda664eed5",
            "toStep": "4d58e0f3-007b-48c2-85f4-2ea67f75c99e",
            "destinationActionStatus": 0,
        },
        {
            "condition": "1",
            "fromStep": "e82b5ab4-d708-4171-9062-e886ac6f71bd",
            "toStep": "5efb0efb-ea0c-4766-b780-07bda664eed5",
            "destinationActionStatus": 0,
        },
        {
            "condition": "2",
            "fromStep": "e82b5ab4-d708-4171-9062-e886ac6f71bd",
            "toStep": "8ab8d270-dbd6-4a51-9d68-228a1c7fd217",
            "destinationActionStatus": 0,
        },
        {
            "condition": "1",
            "fromStep": "80493f4c-0c45-4a4f-9ad4-36bc8a6dab84",
            "toStep": "8bd0316b-a0f7-4f26-be8f-72e5418d91d8",
            "destinationActionStatus": 0,
        },
        {
            "condition": "2",
            "fromStep": "aff01611-87be-4448-bd3e-f7527434fabe",
            "toStep": "a91fd721-7dfd-4c36-94cb-3fd64596cddc",
            "destinationActionStatus": 0,
        },
        {
            "condition": "",
            "fromStep": "8bd0316b-a0f7-4f26-be8f-72e5418d91d8",
            "toStep": "ab899475-2030-4b42-b72a-3f458fdcd13b",
            "destinationActionStatus": 0,
        },
        {
            "condition": "2",
            "fromStep": "80493f4c-0c45-4a4f-9ad4-36bc8a6dab84",
            "toStep": "ab899475-2030-4b42-b72a-3f458fdcd13b",
            "destinationActionStatus": 0,
        },
        {
            "condition": "",
            "fromStep": "ec21b730-635b-42c6-b03c-f1bbb761b875",
            "toStep": "aff01611-87be-4448-bd3e-f7527434fabe",
            "destinationActionStatus": 0,
        },
        {
            "condition": "",
            "fromStep": "8ab8d270-dbd6-4a51-9d68-228a1c7fd217",
            "toStep": "e08c4150-f2b6-4537-a09b-4b5e2ec4a0e3",
            "destinationActionStatus": 0,
        },
        {
            "condition": "1",
            "fromStep": "aff01611-87be-4448-bd3e-f7527434fabe",
            "toStep": "e82b5ab4-d708-4171-9062-e886ac6f71bd",
            "destinationActionStatus": 0,
        },
        {
            "condition": "",
            "fromStep": "ab899475-2030-4b42-b72a-3f458fdcd13b",
            "toStep": "ec21b730-635b-42c6-b03c-f1bbb761b875",
            "destinationActionStatus": 0,
        },
        {
            "condition": "",
            "fromStep": "4d58e0f3-007b-48c2-85f4-2ea67f75c99e",
            "toStep": "f93d6cba-cee5-44f3-a9fd-26437b15dc63",
            "destinationActionStatus": 0,
        },
    ],
}

SAMPLE_PLAYBOOK_WITH_OVERVIEW: SingleJson = {
    "id": 1,
    "identifier": "test-pb",
    "name": "Test Playbook",
    "playbookType": 0,
    "OverviewTemplatesDetails": [
        {
            "Roles": ["Tier 1 Analyst"],
            "OverviewTemplate": {
                "Identifier": "ov-1",
                "Name": "Custom Overview",
                "Creator": "admin",
                "PlaybookDefinitionIdentifier": "test-pb",
                "AlertRuleType": 0,
                "Roles": ["Tier 1 Analyst"],
                "Type": 1,
                "Widgets": [
                    {
                        "Title": "Alert Summary",
                        "WidgetSize": 2,
                        "Order": 1,
                        "Type": 3,
                        "HtmlContent": "<b>[Alert.Name]</b>",
                        "Creator": "admin",
                        "Description": "Header description",
                        "Identifier": "w-uuid-1",
                        "SystemWidgetIdentifier": "sys-w-1",
                    }
                ],
            },
        }
    ],
    "WidgetTemplates": [],
    "steps": [
        {
            "identifier": "step-1",
            "instanceName": "First Step",
            "type": 0,
        },
        {
            "identifier": "step-2",
            "instanceName": "Second Step",
            "type": 0,
        },
    ],
    "stepsRelations": [
        {
            "fromStep": "step-1",
            "toStep": "step-2",
            "condition": "True",
            "destinationActionStatus": 1,
        }
    ],
}


def _assert_deconstructed_files(deconstructed: list[File]) -> None:
    """Asserts that deconstructed files have the expected names and parsed contents."""
    filenames = {f.path for f in deconstructed}
    assert "definition.yaml" in filenames
    assert "trigger.yaml" in filenames
    assert "display_info.yaml" in filenames
    assert "overviews.yaml" in filenames
    assert "release_notes.yaml" in filenames
    assert "steps/first_step_instance_12345.yaml" in filenames
    assert "steps/second_step_instance_87654.yaml" in filenames

    # Verify content of definition.yaml
    definition_file = next(f for f in deconstructed if f.path == "definition.yaml")
    meta = yaml.safe_load(definition_file.content)
    assert meta["identifier"] == "my-playbook-uuid"
    assert meta["name"] == "My Great Playbook"
    assert meta["type"] == "playbook"
    assert meta["category"] == 5
    assert meta["has_restricted_environments"] is False
    assert meta["some_custom_field"] == "customValue"

    # Verify content of trigger.yaml
    trigger_file = next(f for f in deconstructed if f.path == "trigger.yaml")
    trig = yaml.safe_load(trigger_file.content)
    assert trig["identifier"] == "trigger-uuid"
    assert trig["type_"] == "all"
    assert trig["conditions"][0]["field_name"] == "Device"
    assert trig["conditions"][0]["match_type"] == "equal"

    # Verify content of step file
    step_file = next(
        f for f in deconstructed if f.path == "steps/first_step_instance_12345.yaml"
    )
    step = yaml.safe_load(step_file.content)
    assert step["identifier"] == "12345678"
    assert step["type"] == "action"
    assert step["action_provider"] == "Ping"
    assert step["parameters"][0]["name"] == "Host"
    assert step["parameters"][0]["value"] == "8.8.8.8"


def _assert_reconstructed(reconstructed: SingleJson) -> None:
    """Asserts that reconstructed structure is equivalent and valid."""
    assert reconstructed["identifier"] == SAMPLE_FLAT_PLAYBOOK["identifier"]
    assert reconstructed["name"] == SAMPLE_FLAT_PLAYBOOK["name"]
    assert reconstructed["playbookType"] == SAMPLE_FLAT_PLAYBOOK["playbookType"]
    assert reconstructed["categoryId"] == SAMPLE_FLAT_PLAYBOOK["categoryId"]
    assert reconstructed["hasRestrictedEnvironments"] is False
    assert reconstructed["someCustomField"] == "customValue"

    assert (
        reconstructed["trigger"]["identifier"]
        == SAMPLE_FLAT_PLAYBOOK["trigger"]["identifier"]
    )
    assert reconstructed["trigger"]["type"] == SAMPLE_FLAT_PLAYBOOK["trigger"]["type"]
    assert reconstructed["trigger"]["conditions"][0]["fieldName"] == "Device"
    assert "FieldName" not in reconstructed["trigger"]["conditions"][0]

    assert len(reconstructed["steps"]) == 2
    step = next(s for s in reconstructed["steps"] if s.get("identifier") == "12345678")
    assert "Identifier" not in step
    assert step["type"] == 0
    assert step["actionProvider"] == "Ping"
    assert step["parameters"][0]["name"] == "Host"
    assert "Name" not in step["parameters"][0]

    assert len(reconstructed["stepsRelations"]) == 1
    rel = reconstructed["stepsRelations"][0]
    assert rel["condition"] == "Approve"
    assert rel["fromStep"] == "12345678"
    assert rel["toStep"] == "87654321"


def test_deconstruct_and_reconstruct_playbook() -> None:
    """Tests deconstruction and reconstruction of playbooks."""
    # Act - Deconstruct
    deconstructed = PlaybookYAMLConverter.deconstruct_playbook(SAMPLE_FLAT_PLAYBOOK)
    _assert_deconstructed_files(deconstructed)

    # Act - Reconstruct
    files_dict = {
        f.path: f.content.encode("utf-8") if isinstance(f.content, str) else f.content
        for f in deconstructed
    }
    reconstructed = PlaybookYAMLConverter.reconstruct_playbook(files_dict)
    _assert_reconstructed(reconstructed)


def test_reconstruct_real_world_playbook_relations() -> None:
    """Tests reconstruction of step relations from real-world playbook payload."""
    deconstructed = PlaybookYAMLConverter.deconstruct_playbook(
        REAL_WORLD_PLAYBOOK_PAYLOAD
    )
    files_dict = {
        f.path: f.content.encode("utf-8") if isinstance(f.content, str) else f.content
        for f in deconstructed
    }
    reconstructed = PlaybookYAMLConverter.reconstruct_playbook(files_dict)

    # Verify unmapped trigger fields are preserved
    assert reconstructed["trigger"]["reactionLogicalOperator"] == 1
    assert reconstructed["trigger"]["reactionConditions"] is None
    assert reconstructed["trigger"]["executionMode"] == 0

    assert len(reconstructed["stepsRelations"]) == 13

    r1 = next(
        r
        for r in reconstructed["stepsRelations"]
        if r["fromStep"] == "e82b5ab4-d708-4171-9062-e886ac6f71bd"
        and r["toStep"] == "5efb0efb-ea0c-4766-b780-07bda664eed5"
    )
    assert r1["condition"] == "1"

    r2 = next(
        r
        for r in reconstructed["stepsRelations"]
        if r["fromStep"] == "aff01611-87be-4448-bd3e-f7527434fabe"
        and r["toStep"] == "a91fd721-7dfd-4c36-94cb-3fd64596cddc"
    )
    assert r2["condition"] == "2"

    r3 = next(
        r
        for r in reconstructed["stepsRelations"]
        if r["fromStep"] == "5efb0efb-ea0c-4766-b780-07bda664eed5"
        and r["toStep"] == "4d58e0f3-007b-48c2-85f4-2ea67f75c99e"
    )
    assert r3["condition"] == ""


def test_overview_widgets_and_definition_exclusion() -> None:
    """Tests overview template widget preservation and definition.yaml key exclusions."""
    deconstructed = PlaybookYAMLConverter.deconstruct_playbook(
        SAMPLE_PLAYBOOK_WITH_OVERVIEW
    )

    # Verify definition.yaml does not contain duplicated overview keys
    def_file = next(f for f in deconstructed if f.path == "definition.yaml")
    assert b"overview_templates_details" not in def_file.content
    assert b"widget_templates" not in def_file.content

    # Reconstruct
    files_dict = {
        f.path: f.content.encode("utf-8") if isinstance(f.content, str) else f.content
        for f in deconstructed
    }
    reconstructed = PlaybookYAMLConverter.reconstruct_playbook(files_dict)

    # Verify OverviewTemplatesDetails and Widgets are completely preserved
    assert len(reconstructed["OverviewTemplatesDetails"]) == 1
    ov = reconstructed["OverviewTemplatesDetails"][0]
    assert ov["Roles"] == ["Tier 1 Analyst"]
    template = ov["OverviewTemplate"]
    assert template["Name"] == "Custom Overview"
    assert template["Type"] == 1

    assert len(template["Widgets"]) == 1
    widget = template["Widgets"][0]
    assert widget["Title"] == "Alert Summary"
    assert widget["WidgetSize"] == 2
    assert widget["Order"] == 1
    assert widget["Type"] == 3
    assert widget["HtmlContent"] == "<b>[Alert.Name]</b>"
    assert widget["Creator"] == "admin"
    assert widget["Description"] == "Header description"
    assert widget["Identifier"] == "w-uuid-1"
    assert widget["SystemWidgetIdentifier"] == "sys-w-1"

    # Verify destinationActionStatus non-zero value is preserved
    assert len(reconstructed["stepsRelations"]) == 1
    assert reconstructed["stepsRelations"][0]["destinationActionStatus"] == 1

    # Verify destinationActionStatuses is dropped from reconstructed steps
    for step in reconstructed["steps"]:
        assert "destinationActionStatuses" not in step
