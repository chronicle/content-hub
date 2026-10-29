# Copyright 2025 Google LLC
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

import base64
import json
import logging
import pathlib
import re
from typing import TYPE_CHECKING, Any
import uuid
from zipfile import ZipFile

from jinja2 import Environment as JinjaEnvironment
from jinja2 import Template
from requests.exceptions import HTTPError
from TIPCommon.utils import platform_supports_1p_api

from .constants import (
    ACTION_PARAMETER_TYPES,
    BASE_PARAMETER_TYPES,
    CONDITION_MATCH_TYPES,
    CONDITION_OPERATORS,
    CONNECTOR_README,
    INTEGRATION_README_TEMPLATE,
    JOB_README,
    MAPPING_README,
    PLAYBOOK_README_TEMPLATE,
    STEP_TYPE,
    TRIGGER_TYPES,
    VISUAL_FAMILY_README,
    ScriptType,
    WorkflowTypes,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_README_ADDONS: dict[str, dict[str, Any]] = {
    "Integration": {},
    "Mappings": {},
    "Visual Family": {},
    "Playbook": {},
    "Connector": {},
    "Job": {},
    "Block": {},
}


def get_fields(rule: Any) -> list[Any]:
    """Extract iterable fields from either response format."""
    if isinstance(rule, list):
        return rule
    if isinstance(rule, dict):
        if "familyFields" in rule or "systemFields" in rule:
            return rule.get("familyFields", []) + rule.get("systemFields", [])
        if "mapping_rules" in rule:
            return rule.get("mapping_rules", [])
        if "mappingRules" in rule:
            return rule.get("mappingRules", [])
    return []


def get_mapping_rule(r: Any) -> Any:
    """Get the mappingRule dict from either format."""
    if isinstance(r, dict) and "mappingRule" in r:
        return r["mappingRule"]
    return r


if TYPE_CHECKING:
    from collections.abc import Iterator

    from .SiemplifyApiClient import SiemplifyApiClient
    from TIPCommon.types import ChronicleSOAR


class File:
    """Represents a common file object used by the GitManager"""

    def __init__(self, path: str, contents: str | bytes):
        self.path = path
        if isinstance(contents, str):
            contents = contents.encode("utf-8")
        self.content = contents

    def __repr__(self):
        return f"{{Path: {self.path} Contents head: {self.content[:15]}...}}"


class Content:
    def __init__(self):
        self.readme: str | None = None


class Metadata:
    def __init__(self, **kwargs):
        def _get_arg_with_multiple_names(
            args: dict[str, Any],
            arg_name_options: list[str],
            default_value: Any,
        ):
            for name in arg_name_options:
                value = args.get(name)
                if value:
                    return value
            return default_value

        self.system_version = _get_arg_with_multiple_names(
            kwargs,
            ["system_version", "systemVersion"],
            "",
        )
        self.readme_addons = _get_arg_with_multiple_names(
            kwargs,
            ["readme_addons", "readmeAddons"],
            {k: {} for k in DEFAULT_README_ADDONS},
        )
        # Ensure all expected keys exist
        for k in DEFAULT_README_ADDONS:
            self.readme_addons.setdefault(k, {})

        self.settings = kwargs.get("settings", {"update_root_readme": True})

    def get_readme_addon(self, content_type: str, content_name: str) -> str | None:
        if content_type not in self.readme_addons:
            raise KeyError(f"Content Type {content_type} doesn't exist")
        if content_name not in self.readme_addons[content_type]:
            return None
        return self.readme_addons[content_type][content_name]

    def set_readme_addon(
        self,
        content_type: str,
        content_name: str,
        readme: str,
    ) -> None:
        if content_type not in self.readme_addons:
            raise KeyError(f"Content Type {content_type} doesn't exist")
        self.readme_addons[content_type][content_name] = "\n".join(readme.split("\\n"))

    def get_setting_by_name(self, name: str) -> Any:
        if name not in self.settings:
            raise KeyError(f"Setting {name} not found")
        return self.settings[name]


class Connector(Content):
    def __init__(self, connector: dict):
        super().__init__()
        self.raw_data = connector
        for param in self.raw_data["params"]:
            param["creationTimeUnixTimeInMs"] = 0
            param["modificationTimeUnixTimeInMs"] = 0
        self.name = self.raw_data.get("displayName")
        self.description = self.raw_data.get("description")
        self.integration = self.raw_data.get("integration")
        self.integration_version = self.raw_data.get("integrationVersion")
        self.connector_definition_name = self.raw_data.get("connectorDefinitionName")
        self.environment = self.raw_data.get("environment")

    def generate_readme(self, additional_info: str = None) -> None:
        template = CONNECTOR_README
        if additional_info:
            template += additional_info
        readme = Template(template)
        self.readme = readme.render(connector=self.raw_data)

    def iter_files(self) -> Iterator[File]:
        yield File("README.md", self.readme)
        yield File(f"{self.name}.json", json.dumps(self.raw_data, indent=4))


class VisualFamily(Content):
    def __init__(self, visual_family: dict):
        super().__init__()
        if "visualFamilyDataModel" in visual_family:
            visual_family = visual_family["visualFamilyDataModel"]
        self.raw_data = visual_family
        self.name = self.raw_data.get("family")
        self.description = self.raw_data.get("description")
        self.imageBase64 = self.raw_data.get("imageBase64")
        self.rules = self.raw_data.get("rules")
        self.raw_data["id"] = 0
        for rule in self.raw_data["rules"]:
            rule["id"] = 0

    def get_importable_format(self) -> dict:
        return {"visualFamilyDataModel": self.raw_data}

    def iter_files(self) -> Iterator[File]:
        yield File("README.md", self.readme)
        yield File(
            f"{self.name}.json",
            json.dumps(self.get_importable_format(), indent=4),
        )
        yield File(f"{self.name}.png", base64.b64decode(self.imageBase64))

    def generate_readme(self, additional_info: str = None) -> None:
        template = VISUAL_FAMILY_README
        if additional_info:
            template += additional_info
        readme = Template(template)
        self.readme = readme.render(visual_family=self.__dict__)


class Mapping(Content):
    def __init__(self, integration_name: str, records: list[dict], rules: list[dict]):
        super().__init__()
        self.integrationName = integration_name
        self.records = records
        self.rules = rules
        for rec in self.records:
            rec["id"] = 0
            rec["familyId"] = 0
        for rule in self.rules:
            if isinstance(rule, dict) and (
                "familyFields" in rule or "systemFields" in rule
            ):
                for fam_fields in rule.get("familyFields", []) + rule.get(
                    "systemFields", []
                ):
                    if isinstance(fam_fields, dict) and isinstance(
                        fam_fields.get("mappingRule"), dict
                    ):
                        fam_fields["mappingRule"]["id"] = 0
                        fam_fields["mappingRule"]["creationTimeUnixTimeInMs"] = 0
                        fam_fields["mappingRule"]["modificationTimeUnixTimeInMs"] = 0
                    if isinstance(fam_fields, dict):
                        fam_fields["creationTimeUnixTimeInMs"] = 0
                        fam_fields["modificationTimeUnixTimeInMs"] = 0
            elif isinstance(rule, dict):
                rule["id"] = 0
                if "creationTimeUnixTimeInMs" in rule:
                    rule["creationTimeUnixTimeInMs"] = 0
                if "modificationTimeUnixTimeInMs" in rule:
                    rule["modificationTimeUnixTimeInMs"] = 0

    def iter_files(self) -> Iterator[File]:
        yield File("README.md", self.readme)
        yield File(
            f"{self.integrationName}_Records.json",
            json.dumps(self.records, indent=4),
        )
        yield File(
            f"{self.integrationName}_Rules.json",
            json.dumps(self.rules, indent=4),
        )

    def generate_readme(self, additional_info: str = None) -> None:
        template = MAPPING_README
        if additional_info:
            template += additional_info
        readme = Template(template)
        self.readme = readme.render(mappings=self.__dict__)


def _determine_card_name(card: dict) -> str | None:
    raw_name = card.get("name")
    display_name = card.get("displayName")
    if raw_name and str(raw_name).startswith("projects/"):
        return display_name or str(raw_name)
    return display_name or raw_name


def _determine_card_type(card: dict) -> int | None:
    card_type = card.get("type")
    if isinstance(card_type, ScriptType):
        return card_type.value
    if card_type is not None:
        try:
            return int(card_type)
        except (ValueError, TypeError):
            pass
    name_str = str(card.get("name", "")).lower()
    if "actiontype" in card or "/actions/" in name_str or "/actions" in name_str:
        return ScriptType.ACTION.value
    if "jobtype" in card or "/jobs/" in name_str or "/jobs" in name_str:
        return ScriptType.JOB.value
    if "connectortype" in card or "/connectors/" in name_str or "/connectors" in name_str:
        return ScriptType.CONNECTOR.value
    if "managertype" in card or "/managers/" in name_str or "/managers" in name_str:
        return ScriptType.MANAGER.value
    return None


class Integration(Content):
    def __init__(self, integration_card: dict, zip_buffer):
        super().__init__()
        self.zip_buffer = zip_buffer
        self.integration_card = integration_card

        self.zipfile = ZipFile(zip_buffer)
        self.identifier = self.integration_card.get("identifier")
        self.staging = self.integration_card.get("Staging")
        custom_card_val = next(
            (
                self.integration_card[k]
                for k in ("isCustomIntegration", "custom", "Custom", "IsCustom")
                if self.integration_card.get(k) is not None
            ),
            None,
        )
        has_def = False
        try:
            self.definition = json.loads(
                self.zipfile.read(f"Integration-{self.identifier}.def"),
            )
            has_def = True
        except KeyError:
            self.definition = json.loads(
                self.zipfile.read(f"Integration-{self.identifier}.json"),
            )
        if custom_card_val is not None:
            self.isCustom = bool(custom_card_val)
        else:
            custom_def_val = next(
                (
                    self.definition[k]
                    for k in ("isCustomIntegration", "custom", "Custom", "IsCustom")
                    if self.definition.get(k) is not None
                ),
                None,
            )
            if custom_def_val is not None:
                self.isCustom = bool(custom_def_val)
            else:
                self.isCustom = not has_def

        self.version = self.definition.get("Version")
        if not self.isCustom:
            self.definition["IsCustom"] = False

        self.actions = []
        self.jobs = []
        self.connectors = []
        self.managers = []
        self.dependencies = []
        self.has_resources = False
        for file in [x for x in self.zipfile.namelist() if not x.endswith("/")]:
            try:
                if file.endswith(".py"):
                    continue
                file_lower = file.lower()
                if file_lower.startswith("actions") and not file_lower.startswith("actionsscripts"):
                    item = json.loads(self.zipfile.read(file))
                    if isinstance(item, dict):
                        item_name = item.get("name") or item.get("Name") or pathlib.Path(file).stem
                        item.setdefault("name", item_name)
                        item.setdefault("displayName", item.get("DisplayName", item_name))
                        item.setdefault("type", ScriptType.ACTION.value)
                        item.setdefault("integrationIdentifier", self.identifier)
                        self.actions.append(item)
                elif file_lower.startswith("jobs") and not file_lower.startswith(("jobsscrips", "jobsscripts")):
                    item = json.loads(self.zipfile.read(file))
                    if isinstance(item, dict):
                        item_name = item.get("name") or item.get("Name") or pathlib.Path(file).stem
                        item.setdefault("name", item_name)
                        item.setdefault("displayName", item.get("DisplayName", item_name))
                        item.setdefault("type", ScriptType.JOB.value)
                        item.setdefault("integrationIdentifier", self.identifier)
                        self.jobs.append(item)
                elif file_lower.startswith("connectors") and not file_lower.startswith("connectorsscripts"):
                    item = json.loads(self.zipfile.read(file))
                    if isinstance(item, dict):
                        item_name = item.get("name") or item.get("Name") or pathlib.Path(file).stem
                        item.setdefault("name", item_name)
                        item.setdefault("displayName", item.get("DisplayName", item_name))
                        item.setdefault("type", ScriptType.CONNECTOR.value)
                        item.setdefault("integrationIdentifier", self.identifier)
                        self.connectors.append(item)
                elif (
                    not self.isCustom
                    and file_lower.startswith("managers")
                    and file.endswith((".managerdef", ".json"))
                ):
                    item = json.loads(self.zipfile.read(file))
                    if isinstance(item, dict):
                        item_name = item.get("name") or item.get("Name") or pathlib.Path(file).stem
                        item.setdefault("name", item_name)
                        item.setdefault("displayName", item.get("DisplayName", item_name))
                        item.setdefault("type", ScriptType.MANAGER.value)
                        item.setdefault("integrationIdentifier", self.identifier)
                        self.managers.append(item)
                elif self.isCustom and file.startswith("Managers"):
                    self.managers.append(file)
                elif file.startswith("Dependencies"):
                    self.dependencies.append(file)
                elif file.startswith("Resources/" + self.identifier + ".svg"):
                    self.has_resources = True
            except json.JSONDecodeError:
                LOGGER.warning("Skipping %s - not valid JSON.", file)

    def get_all_items(self):
        items = []
        for x in self.actions + self.jobs + self.connectors + self.managers:
            if isinstance(x, dict):
                items.append(x)
        return items

    def get_script(self, name: str, script_type: ScriptType) -> str:
        candidates = []
        if script_type == ScriptType.JOB:
            candidates = [
                f"JobsScripts/{name}.py",
                f"JobsScrips/{name}.py",
                f"Jobs/{name}.py",
                f"jobs/{name}.py",
            ]
        elif script_type == ScriptType.ACTION:
            candidates = [
                f"ActionsScripts/{name}.py",
                f"ActionsDefinitions/{name}.py",
                f"Actions/{name}.py",
                f"actions/{name}.py",
            ]
        elif script_type == ScriptType.CONNECTOR:
            candidates = [
                f"ConnectorsScripts/{name}.py",
                f"Connectors/{name}.py",
                f"connectors/{name}.py",
            ]
        elif script_type == ScriptType.MANAGER:
            candidates = [
                f"Managers/{name}.py",
                f"managers/{name}.py",
            ]
        for path in candidates:
            try:
                return self.zipfile.read(path).decode("utf-8")
            except KeyError:
                continue
        for item in self.zipfile.namelist():
            if item.endswith(f"/{name}.py") or item == f"{name}.py":
                return self.zipfile.read(item).decode("utf-8")
        raise KeyError(f"Script for {name} ({script_type}) not found in archive.")

    def get_zip_as_base64(self):
        return base64.b64encode(self.zip_buffer.getvalue()).decode("utf-8")

    def get_zip_binary(self):
        return self.zip_buffer.getvalue()

    def generate_readme(self, additional_info: str = None):
        env = JinjaEnvironment()
        env.filters.update(
            {
                "action_param_type": lambda x: ACTION_PARAMETER_TYPES.get(x),
                "base_param_type": lambda x: BASE_PARAMETER_TYPES.get(x),
            },
        )
        template = INTEGRATION_README_TEMPLATE
        if additional_info:
            template += additional_info
        readme = env.from_string(template)
        if not self.isCustom:
            cards = self.integration_card.get("cards") or []
            if (
                isinstance(cards, list)
                and cards
                and isinstance(cards[0], dict)
                and "cards" in cards[0]
            ):
                matched = next(
                    (x for x in cards if x.get("identifier") == self.identifier),
                    cards[0],
                )
                cards = matched.get("cards", [])

            if cards:
                custom_action_names = set()
                custom_job_names = set()
                custom_connector_names = set()

                for c in cards:
                    is_custom = bool(
                        c.get("custom") is True
                        or c.get("isCustom") is True
                        or c.get("IsCustom") is True
                        or c.get("Custom") is True
                    )
                    if not is_custom:
                        continue
                    c_name = _determine_card_name(c)
                    if not c_name:
                        continue
                    t_val = _determine_card_type(c)
                    if t_val == ScriptType.ACTION.value:
                        custom_action_names.add(c_name)
                    elif t_val == ScriptType.JOB.value:
                        custom_job_names.add(c_name)
                    elif t_val == ScriptType.CONNECTOR.value:
                        custom_connector_names.add(c_name)

                custom_actions = [
                    x
                    for x in self.actions
                    if (
                        x.get("displayName") in custom_action_names
                        or x.get("name") in custom_action_names
                        or x.get("Name") in custom_action_names
                    )
                ]
                custom_jobs = [
                    x
                    for x in self.jobs
                    if (
                        x.get("displayName") in custom_job_names
                        or x.get("name") in custom_job_names
                        or x.get("Name") in custom_job_names
                    )
                ]
                custom_connectors = [
                    x
                    for x in self.connectors
                    if (
                        x.get("displayName") in custom_connector_names
                        or x.get("name") in custom_connector_names
                        or x.get("Name") in custom_connector_names
                    )
                ]
            else:
                custom_actions = [
                    x
                    for x in self.actions
                    if (
                        x.get("Custom") is True
                        or x.get("custom") is True
                        or x.get("IsCustom") is True
                        or x.get("isCustom") is True
                    )
                ]
                custom_jobs = [
                    x
                    for x in self.jobs
                    if (
                        x.get("Custom") is True
                        or x.get("custom") is True
                        or x.get("IsCustom") is True
                        or x.get("isCustom") is True
                    )
                ]
                custom_connectors = [
                    x
                    for x in self.connectors
                    if (
                        x.get("Custom") is True
                        or x.get("custom") is True
                        or x.get("IsCustom") is True
                        or x.get("isCustom") is True
                    )
                ]

            integration = {
                "dependencies": self.dependencies,
                "definition": self.definition,
                "actions": custom_actions,
                "jobs": custom_jobs,
                "connectors": custom_connectors,
                "has_resources": self.has_resources,
            }
            self.readme = readme.render(integration=integration)
        else:
            self.readme = readme.render(integration=self.__dict__)

    def __repr__(self):
        return self.identifier

    def iter_files(self, api: SiemplifyApiClient) -> Iterator[File]:
        """Iterates all files in integration.

        If the integration is custom, it will only return custom and mandatory files.
        if not, it will iterate all the files in the exported zip. It yields tuples of
        (relative_path, data)

        Args:
            api: SiemplifyApiClient object - to diff between custom and commercial scripts

        Returns: A generator of File object instances representing the integration

        """
        yield File("README.md", self.readme)
        if not self.isCustom:
            self.definition["Custom"] = False
            yield File(
                f"Integration-{self.identifier}.def",
                json.dumps(self.definition, indent=4),
            )

            if self.has_resources:
                for file in self.zipfile.namelist():
                    if file.startswith("Resources/") and not file.endswith("/"):
                        yield File(file, self.zipfile.read(file))

            cards = self.integration_card.get("cards")
            if not cards and api:
                try:
                    response = api.get_ide_cards(self.identifier)
                    if isinstance(response, dict) and "cards" in response:
                        cards = response.get("cards", [])
                    elif isinstance(response, list):
                        cards = response
                except (KeyError, AttributeError, TypeError, ValueError) as e:
                    LOGGER.warning(
                        "Could not fetch ide cards for %s: %s", self.identifier, e
                    )

            if (
                isinstance(cards, list)
                and cards
                and isinstance(cards[0], dict)
                and "cards" in cards[0]
            ):
                matched = next(
                    (
                        x
                        for x in cards
                        if x.get("identifier") == self.identifier
                    ),
                    cards[0],
                )
                cards = matched.get("cards", [])

            for card in cards or []:
                is_custom = bool(
                    card.get("custom") is True
                    or card.get("isCustom") is True
                    or card.get("IsCustom") is True
                    or card.get("Custom") is True
                )
                if not is_custom:
                    continue

                card_name = _determine_card_name(card)
                if not card_name:
                    continue

                type_val = _determine_card_type(card)
                if type_val is None:
                    continue

                collection_map = {
                    ScriptType.ACTION.value: "actions",
                    ScriptType.JOB.value: "jobs",
                    ScriptType.CONNECTOR.value: "connectors",
                    ScriptType.MANAGER.value: "managers",
                }
                col = collection_map.get(type_val, "actions")
                raw_name = str(card.get("name", ""))
                item_ref = raw_name if raw_name.startswith("projects/") else card.get("id")
                if (
                    platform_supports_1p_api()
                    and item_ref is not None
                    and not str(item_ref).startswith("projects/")
                    and "integrations/" not in str(item_ref)
                ):
                    item_ref = f"integrations/{self.identifier}/{col}/{item_ref}"

                definition = None
                if api:
                    try:
                        res = api.get_ide_item(item_ref, card.get("type") or type_val)
                        if isinstance(res, dict):
                            definition = dict(res)
                            definition["id"] = 0
                            if "name" in definition and str(definition["name"]).startswith("projects/"):
                                definition["name"] = card_name
                            definition.setdefault("Name", card_name)
                            definition.setdefault("displayName", card_name)
                            definition.setdefault("DisplayName", card_name)
                    except Exception as e:
                        LOGGER.warning(
                            "Could not get ide item for %s: %s", card_name, e
                        )

                if type_val == ScriptType.ACTION.value:
                    if not definition:
                        matched = next(
                            (
                                x
                                for x in self.actions
                                if (
                                    x.get("name") == card_name
                                    or x.get("Name") == card_name
                                    or x.get("displayName") == card_name
                                    or x.get("DisplayName") == card_name
                                )
                            ),
                            None,
                        )
                        definition = dict(matched) if matched else {"name": card_name}
                        definition["id"] = 0
                    yield File(
                        f"ActionsDefinitions/{card_name}.actiondef",
                        json.dumps(definition, indent=4),
                    )
                    script = None
                    if isinstance(definition, dict):
                        script = definition.get("script") or definition.get("Script")
                    if not script:
                        try:
                            script = self.get_script(card_name, ScriptType.ACTION)
                        except (KeyError, FileNotFoundError):
                            pass
                    yield File(
                        f"ActionsScripts/{card_name}.py",
                        script or "",
                    )

                elif type_val == ScriptType.JOB.value:
                    if not definition:
                        matched = next(
                            (
                                x
                                for x in self.jobs
                                if (
                                    x.get("name") == card_name
                                    or x.get("Name") == card_name
                                    or x.get("displayName") == card_name
                                    or x.get("DisplayName") == card_name
                                )
                            ),
                            None,
                        )
                        definition = dict(matched) if matched else {"name": card_name}
                        definition["id"] = 0
                    yield File(
                        f"Jobs/{card_name}.jobdef",
                        json.dumps(definition, indent=4),
                    )
                    script = None
                    if isinstance(definition, dict):
                        script = definition.get("script") or definition.get("Script")
                    if not script:
                        try:
                            script = self.get_script(card_name, ScriptType.JOB)
                        except (KeyError, FileNotFoundError):
                            pass
                    yield File(
                        f"JobsScripts/{card_name}.py",
                        script or "",
                    )

                elif type_val == ScriptType.CONNECTOR.value:
                    if not definition:
                        matched = next(
                            (
                                x
                                for x in self.connectors
                                if (
                                    x.get("name") == card_name
                                    or x.get("Name") == card_name
                                    or x.get("displayName") == card_name
                                    or x.get("DisplayName") == card_name
                                )
                            ),
                            None,
                        )
                        definition = dict(matched) if matched else {"name": card_name}
                        definition["id"] = 0
                    yield File(
                        f"Connectors/{card_name}.connectordef",
                        json.dumps(definition, indent=4),
                    )
                    script = None
                    if isinstance(definition, dict):
                        script = definition.get("script") or definition.get("Script")
                    if not script:
                        try:
                            script = self.get_script(card_name, ScriptType.CONNECTOR)
                        except (KeyError, FileNotFoundError):
                            pass
                    yield File(
                        f"ConnectorsScripts/{card_name}.py",
                        script or "",
                    )

                elif type_val == ScriptType.MANAGER.value:
                    if not definition:
                        matched = next(
                            (
                                x
                                for x in self.managers
                                if isinstance(x, dict)
                                and (
                                    x.get("name") == card_name
                                    or x.get("Name") == card_name
                                    or x.get("displayName") == card_name
                                    or x.get("DisplayName") == card_name
                                )
                            ),
                            None,
                        )
                        definition = dict(matched) if matched else {"name": card_name}
                        definition["id"] = 0
                    yield File(
                        f"Managers/{card_name}.managerdef",
                        json.dumps(definition, indent=4),
                    )
                    script = None
                    if isinstance(definition, dict):
                        script = definition.get("script") or definition.get("Script")
                    if not script:
                        try:
                            script = self.get_script(card_name, ScriptType.MANAGER)
                        except (KeyError, FileNotFoundError):
                            pass
                    yield File(
                        f"Managers/{card_name}.py",
                        script or "",
                    )
        else:
            for file in self.zipfile.namelist():
                content = self.zipfile.read(file)
                if content:  # filters folders
                    yield File(file, content)


class Workflow(Content):
    def __init__(self, raw_data: dict):
        super().__init__()
        self.raw_data = raw_data
        self.raw_data["id"] = 0
        if "trigger" in self.raw_data and self.raw_data["trigger"] is not None:
            self.raw_data["trigger"]["id"] = 0
        self.name = self.raw_data.get("name")
        self.description = self.raw_data.get("description")
        self.type = WorkflowTypes(
            self.raw_data.get("playbookType", WorkflowTypes.PLAYBOOK.value)
        )
        self.priority = self.raw_data.get("priority")
        self.isDebugMode = self.raw_data.get("isDebugMode", None)
        self.version = self.raw_data.get("version")
        self.trigger = self.raw_data.get("trigger")
        self.steps = self.raw_data.get("steps") or []
        self.isEnabled = self.raw_data.get("isEnabled")
        self.category = self.raw_data.get("categoryName", "Default")
        self.environments = self.raw_data.get("environments")
        self.modification_time = self.raw_data.get("modificationTimeUnixTimeInMs", 0)

    def __hash__(self):
        """Used to remove duplicates in workflow lists"""
        return hash(self.name)

    def __eq__(self, other):
        """Used to remove duplicates in workflow lists"""
        return self.name == getattr(other, "name", None)

    def generate_readme(self, additional_info: str = None):
        env = JinjaEnvironment()
        env.globals["WorkflowTypes"] = WorkflowTypes
        env.filters.update(
            {
                "trigger_type": lambda x: TRIGGER_TYPES.get(x),
                "condition_operator": lambda x: CONDITION_OPERATORS.get(x),
                "condition_match_type": lambda x: CONDITION_MATCH_TYPES.get(x),
                "split_action_name": lambda x: x.split("_", 1)[1] if "_" in x else x,
            },
        )
        template = PLAYBOOK_README_TEMPLATE
        if additional_info:
            template += additional_info
        readme = env.from_string(template)
        self.readme = readme.render(
            playbook=self.__dict__,
            involved_blocks=self.get_involved_blocks(),
        )

    def iter_files(self) -> Iterator[File]:
        yield File(self.name + ".json", json.dumps(self.raw_data, indent=4))
        yield File("README.md", self.readme)

    def get_involved_blocks(self):
        return [x for x in self.steps if x.get("type") == 5]

    def update_instance_name_in_steps(
        self,
        api: SiemplifyApiClient,
        chronicle_soar: ChronicleSOAR,
    ) -> None:
        """Updates name of instances in the steps."""
        for step in self.steps:
            if (
                step.get("type") == STEP_TYPE
                and step.get("actionProvider") == "Scripts"
            ):
                self._update_instance_display_names_for_step(step, api, chronicle_soar)

    def _is_integration_instance_param(
        self,
        param_name: str | None,
        param_value: str | None,
    ) -> bool:
        """Checks if a parameter is a valid integration instance parameter."""
        return param_name in (
            "IntegrationInstance",
            "FallbackIntegrationInstance",
        ) and self._is_valid_instance_id(param_value)

    def _update_instance_display_names_for_step(
        self,
        step: dict,
        api: SiemplifyApiClient,
        chronicle_soar: ChronicleSOAR,
    ) -> None:
        """Updates display names for integration instance parameters in a step.

        Args:
            step (dict): The workflow step dictionary to process.
            api (SiemplifyApiClient): An API client instance used to fetch
                integration instance names.
        """
        integration_name = step["integration"]

        for param in step.get("parameters", []):
            param_name = param.get("name")
            param_value = param.get("value")
            try:
                if not self._is_integration_instance_param(param_name, param_value):
                    continue

                display_name = api.get_integration_instance_name(
                    chronicle_soar,
                    integration_name,
                    param_value,
                    self.environments,
                )

                match param_name:
                    case "IntegrationInstance":
                        param["InstanceDisplayName"] = display_name
                    case "FallbackIntegrationInstance":
                        param["FallbackInstanceDisplayName"] = display_name
            except HTTPError as e:
                # ignoring 404 errors as they expected in migrations between instances.
                if e.response is not None and hasattr(e.response, "status_code"):
                    status_code = e.response.status_code
                    if status_code != 404:
                        raise e
                else:
                    # TIPCommon is re-raising HTTPError without response object
                    # Try to extract status code from the error message itself
                    error_msg = str(e)
                    status_code_match = re.search(r"(\d{3})\s+Client Error", error_msg)
                    if status_code_match:
                        status_code = int(status_code_match.group(1))
                        if status_code != 404:
                            raise e
                    else:
                        # can't determine the status code
                        raise e

    def _is_valid_instance_id(self, instance_id: str) -> bool:
        try:
            val = uuid.UUID(instance_id, version=4)

        except (TypeError, ValueError):
            return False

        return str(val) == instance_id and val.version == 4


class Job(Content):
    def __init__(self, raw_data: dict):
        super().__init__()
        raw_data["id"] = 0
        self.raw_data = raw_data
        self.name = self.raw_data.get("name")
        display_name = self.raw_data.get("displayName") or self.raw_data.get("name")
        if isinstance(display_name, str):
            display_name = " ".join(display_name.split())
        self.displayName = display_name
        self.raw_data["displayName"] = display_name
        self.integration = self.raw_data.get("integration")
        self.description = self.raw_data.get("description")
        self.parameters = self.raw_data.get("parameters")
        self.runIntervalInSeconds = self.raw_data.get(
            "runIntervalInSeconds"
        ) or self.raw_data.get("intervalSeconds")

    def generate_readme(self, additional_info: str = None) -> None:
        env = JinjaEnvironment()
        env.filters.update({"base_param_type": lambda x: BASE_PARAMETER_TYPES.get(x)})
        template = JOB_README
        if additional_info:
            template += additional_info
        readme = env.from_string(template)
        self.readme = readme.render(job=self.__dict__)

    def iter_files(self) -> Iterator[File]:
        name = self.displayName or self.name
        name = name.replace("/", "_")
        yield File(f"Jobs/{name}.json", json.dumps(self.raw_data, indent=4))


class IntegrationInstance(Content):
    """Represents an integration instance configuration."""

    def __init__(self, raw_data: dict[str, Any]):
        super().__init__()
        self.raw_data = raw_data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntegrationInstance:
        """Creates an IntegrationInstance from a dictionary."""
        return cls(data)

    def to_1p(self, identifier: str) -> dict[str, Any]:
        """Converts instance configuration to 1P payload shape."""
        settings_payload = self.raw_data.get("settings", {})
        params = []
        for setting in settings_payload.get("settings", []):
            params.append(
                {
                    "description": setting.get("propertyDescription") or None,
                    "mandatory": setting.get("isMandatory") or False,
                    "type": setting.get("propertyType"),
                    "id": setting.get("id"),
                    "displayName": setting.get("propertyDisplayName"),
                    "propertyName": setting.get("propertyName"),
                    "value": setting.get("value"),
                }
            )

        return {
            "name": f"projects/project/locations/location/instances/instance/integrations/{self.raw_data.get('integrationIdentifier')}/integrationInstances/{identifier}",
            "environment": self.raw_data.get("environment"),
            "identifier": identifier,
            "configured": True,
            "remote": None,
            "parameters": params,
            "integrationIdentifier": self.raw_data.get("integrationIdentifier"),
            "description": settings_payload.get("instanceDescription") or None,
            "displayName": settings_payload.get("instanceName"),
        }
