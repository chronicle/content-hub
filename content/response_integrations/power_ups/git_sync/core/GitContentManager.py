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

import json
import pathlib
import stat
import zipfile
from io import BytesIO
from typing import TYPE_CHECKING, Any

from .definitions import (
    Connector,
    File,
    Integration,
    Job,
    Mapping,
    Metadata,
    VisualFamily,
    Workflow,
)
from TIPCommon.utils import platform_supports_1p_api

if TYPE_CHECKING:
    from .GitManager import Git
    from .SiemplifyApiClient import SiemplifyApiClient

INTEGRATIONS_PATH = "Integrations"
PLAYBOOKS_PATH = "Playbooks"
BLOCKS_PATH = "Blocks"
CONNECTORS_PATH = "Connectors"
JOBS_PATH = "Jobs"
MAPPINGS_PATH = "Ontology/Mappings"
VISUAL_FAMILIES_PATH = "Ontology/VisualFamilies"
SIMULATED_CASES_PATH = "SimulatedCases"
METADATA_FILE = "GitSync.json"
SETTINGS_PATH = "Settings"
INTEGRATION_INSTANCES_FILE = f"{SETTINGS_PATH}/integrationInstances.json"
DYNAMIC_PARAMS_FILES = f"{SETTINGS_PATH}/dynamicParameters.json"
ENVIRONMENTS_FILE = f"{SETTINGS_PATH}/environments.json"
LOGO_FILE = f"{SETTINGS_PATH}/logo.json"
TAGS_FILE = f"{SETTINGS_PATH}/tags.json"
STAGES_FILE = f"{SETTINGS_PATH}/stages.json"
CASE_CLOSE_REASONS_FILE = f"{SETTINGS_PATH}/caseCloseCauses.json"
CASE_TITLES_FILE = f"{SETTINGS_PATH}/caseTitles.json"
NETWORKS_FILE = f"{SETTINGS_PATH}/networks.json"
DOMAINS_FILE = f"{SETTINGS_PATH}/domains.json"
CUSTOM_LISTS_FILE = f"{SETTINGS_PATH}/customLists.json"
EMAIL_TEMPLATES_FILE = f"{SETTINGS_PATH}/emailTemplates.json"
DENYLIST_FILE = f"{SETTINGS_PATH}/blacklists.json"
SLA_DEFINITIONS_FILE = f"{SETTINGS_PATH}/slaDefinitions.json"


class GitContentManager:
    def __init__(self, git: Git, api: SiemplifyApiClient, deconstruct_playbooks: bool = True):
        self.git = git
        self.api = api
        self.deconstruct_playbooks = deconstruct_playbooks
        self._metadata = None

    @property
    def metadata(self):
        if not self._metadata:
            self._metadata = self.get_metadata()
        return self._metadata

    def get_metadata(self) -> Metadata:
        try:
            metadata = json.loads(self.git.get_file_contents_from_path(METADATA_FILE))
            metadata = Metadata(**metadata)
        except KeyError:
            metadata = Metadata()
        except ValueError as e:
            raise Exception(f"GitSync.json metadata file is malformed: {e}")
        return metadata

    def push_metadata(self) -> None:
        self._push_file(METADATA_FILE, self.metadata.__dict__)

    def get_integration(self, integration_name: str) -> Integration | None:
        """Get integration as Integration object from the repo

        Args:
            integration_name: Integration name

        Returns: An Integration object, or None if the integration doesn't exist

        """
        try:
            zip_buffer = BytesIO()
            definition = None
            with zipfile.ZipFile(
                zip_buffer,
                "a",
                zipfile.ZIP_DEFLATED,
                False,
            ) as zip_file:
                for file in self.git.get_file_objects_from_path(
                    f"Integrations/{integration_name}",
                ):
                    if file.path in (
                        f"Integration-{integration_name}.def",
                        f"Integration-{integration_name}.json",
                    ):
                        definition = json.loads(file.content)
                    zip_file.writestr(file.path, file.content)
            zip_buffer.seek(0)
            if definition is None:
                raise KeyError(f"Definition file for integration {integration_name} not found.")
            return Integration(
                {
                    "identifier": integration_name,
                    "isCustomIntegration": definition.get("IsCustom") or definition.get("Custom", False),
                    "Staging": definition.get("Staging", "False"),
                },
                zip_buffer,
            )
        except KeyError:
            return None

    def get_integrations(self) -> list[Integration]:
        try:
            for integration in self.git.get_raw_object_from_path(
                INTEGRATIONS_PATH,
            ).items():
                if integration.mode == stat.S_IFDIR:
                    yield self.get_integration(integration.path.decode("utf-8"))
        except KeyError:
            return []

    def _reconstruct_deconstructed_workflows(self, base_path: str) -> list[Workflow]:
        """Finds and reconstructs all deconstructed playbooks/blocks under base_path."""
        try:
            all_files = self.git.get_file_objects_from_path(base_path)
        except KeyError:
            return []

        definition_paths = {}
        for f in all_files:
            p = pathlib.Path(f.path)
            if p.name == "definition.yaml":
                playbook_dir_path = str(p.parent)
                definition_paths[playbook_dir_path] = {}

        for f in all_files:
            p = pathlib.Path(f.path)
            for pb_dir in definition_paths:
                if f.path.startswith(pb_dir + "/"):
                    rel_path = f.path[len(pb_dir) + 1:]
                    definition_paths[pb_dir][rel_path] = f.content
                    break
                elif p.name == "definition.yaml" and str(p.parent) == pb_dir:
                    definition_paths[pb_dir]["definition.yaml"] = f.content
                    break

        from .PlaybookYAMLConverter import PlaybookYAMLConverter
       
        is_1p = platform_supports_1p_api()
        workflows = []
        for pb_dir, files_dict in definition_paths.items():
            try:
                playbook_dict = PlaybookYAMLConverter.reconstruct_playbook(files_dict, is_1p=is_1p)
                parts = pb_dir.split("/")
                if len(parts) >= 2:
                    category_name = parts[-2]
                    playbook_dict["CategoryName"] = category_name
                    if "Definition" in playbook_dict:
                        playbook_dict["Definition"]["CategoryName"] = category_name
                workflows.append(Workflow(playbook_dict))
            except Exception as e:
                self.git.logger.error(f"Failed to reconstruct deconstructed playbook in {pb_dir}: {e}")
                self.git.logger.exception(e)
        return workflows

    def get_playbook(self, playbook_name: str) -> Workflow | None:
        """Reads a playbook or block from the repo object store

        Args:
            playbook_name: Name of the playbook or block, or None if the workflow doesn't exist

        Returns: A Workflow instance

        """
        for wf in self._reconstruct_deconstructed_workflows(PLAYBOOKS_PATH):
            if wf.name == playbook_name:
                return wf
        for wf in self._reconstruct_deconstructed_workflows(BLOCKS_PATH):
            if wf.name == playbook_name:
                return wf

        try:
            for playbook in self.git.get_file_objects_from_path(PLAYBOOKS_PATH):
                if pathlib.Path(playbook.path).name == f"{playbook_name}.json":
                    return Workflow(json.loads(playbook.content))
            for block in self.git.get_file_objects_from_path(BLOCKS_PATH):
                if block.path.endswith(f"/{playbook_name}.json"):
                    return Workflow(json.loads(block.content))
        except KeyError:
            return None
        return None

    def get_playbooks(self) -> list[Workflow]:
        for wf in self._reconstruct_deconstructed_workflows(PLAYBOOKS_PATH):
            yield wf
        for wf in self._reconstruct_deconstructed_workflows(BLOCKS_PATH):
            yield wf

        try:
            for playbook in self.git.get_file_objects_from_path(PLAYBOOKS_PATH):
                if pathlib.Path(playbook.path).suffix == ".json":
                    yield Workflow(json.loads(playbook.content))
            for block in self.git.get_file_objects_from_path(BLOCKS_PATH):
                if block.path.endswith(".json"):
                    yield Workflow(json.loads(block.content))
        except KeyError:
            return []

    def get_connector(self, connector_name: str) -> Connector | None:
        """Reads a connector instance from the repo

        Args:
            connector_name: Name of the connector, or None if the connector doesn't exist

        Returns: A Connector object

        """
        try:
            for connector in self.git.get_file_objects_from_path(CONNECTORS_PATH):
                if pathlib.Path(connector.path).name == f"{connector_name}.json":
                    return Connector(json.loads(connector.content))
        except KeyError:
            return None

    def get_connectors(self) -> list[Connector]:
        try:
            for connector in self.git.get_file_objects_from_path(CONNECTORS_PATH):
                if pathlib.Path(connector.path).suffix == ".json":
                    yield Connector(json.loads(connector.content))
        except KeyError:
            return []

    def get_job(self, job_name: str) -> Job | None:
        try:
            return Job(
                json.loads(
                    self.git.get_file_contents_from_path(
                        f"{JOBS_PATH}/{job_name}.json",
                    ),
                ),
            )
        except KeyError:
            return None

    def get_jobs(self) -> list[Job]:
        try:
            for job in self.git.get_file_objects_from_path(JOBS_PATH):
                if pathlib.Path(job.path).suffix == ".json":
                    yield Job(json.loads(job.content))
        except KeyError:
            return []

    def get_mapping(self, source_name) -> Mapping | None:
        """Reads ontology mappings from the repo

        Args:
            source_name: Source integration name

        Returns: A Mapping object, or None if the mappings doesn't exist

        """
        try:
            records = json.loads(
                self.git.get_file_contents_from_path(
                    f"{MAPPINGS_PATH}/{source_name}/{source_name}_Records.json",
                ),
            )

            rules = json.loads(
                self.git.get_file_contents_from_path(
                    f"{MAPPINGS_PATH}/{source_name}/{source_name}_Rules.json",
                ),
            )

            return Mapping(source_name, records, rules)
        except KeyError:
            return None

    def get_mappings(self) -> list[Mapping]:
        try:
            for mappings in self.git.get_raw_object_from_path(MAPPINGS_PATH):
                yield self.get_mapping(mappings.decode("utf-8"))
        except KeyError:
            return []

    def get_visual_family(self, family_name: str) -> VisualFamily | None:
        """Reads a visual family from the repo

        Args:
            family_name: Name of the visual family

        Returns: A VisualFamily object, or None if the visual family doesn't exist

        """
        try:
            return VisualFamily(
                json.loads(
                    self.git.get_file_contents_from_path(
                        f"{VISUAL_FAMILIES_PATH}/{family_name}/{family_name}.json",
                    ),
                ),
            )
        except KeyError:
            return None

    def get_visual_families(self) -> list[VisualFamily]:
        try:
            for vf in self.git.get_raw_object_from_path(VISUAL_FAMILIES_PATH):
                yield self.get_visual_family(vf.decode("utf-8"))
        except KeyError:
            return []

    def get_simulated_case(self, case_name: str) -> dict | None:
        return json.loads(
            self._get_file_or_default(f"{SIMULATED_CASES_PATH}/{case_name}.case"),
        )

    def get_simulated_cases(self) -> list[dict]:
        try:
            for case in self.git.get_file_objects_from_path(SIMULATED_CASES_PATH):
                if case.path.endswith(".case"):
                    yield json.loads(case.content)
        except KeyError:
            return []

    def get_integration_instances(self) -> list[dict]:
        return json.loads(self._get_file_or_default(INTEGRATION_INSTANCES_FILE, "[]"))

    def get_dynamic_parameters(self) -> list[dict]:
        return json.loads(self._get_file_or_default(DYNAMIC_PARAMS_FILES, "[]"))

    def get_environments(self) -> list[dict]:
        return json.loads(self._get_file_or_default(ENVIRONMENTS_FILE, "[]"))

    def get_logo(self) -> dict:
        return json.loads(self._get_file_or_default(LOGO_FILE, "{}"))

    def get_tags(self) -> list[dict]:
        return json.loads(self._get_file_or_default(TAGS_FILE, "[]"))

    def get_stages(self) -> list[dict]:
        return json.loads(self._get_file_or_default(STAGES_FILE, "[]"))

    def get_case_close_causes(self) -> list[dict]:
        return json.loads(self._get_file_or_default(CASE_CLOSE_REASONS_FILE, "[]"))

    def get_case_titles(self) -> list[dict]:
        return json.loads(self._get_file_or_default(CASE_TITLES_FILE, "[]"))

    def get_networks(self) -> list[dict]:
        return json.loads(self._get_file_or_default(NETWORKS_FILE, "[]"))

    def get_domains(self) -> list[dict]:
        return json.loads(self._get_file_or_default(DOMAINS_FILE, "[]"))

    def get_custom_lists(self) -> list[dict]:
        return json.loads(self._get_file_or_default(CUSTOM_LISTS_FILE, "[]"))

    def get_email_templates(self) -> list[dict]:
        return json.loads(self._get_file_or_default(EMAIL_TEMPLATES_FILE, "[]"))

    def get_denylists(self) -> list[dict]:
        return json.loads(self._get_file_or_default(DENYLIST_FILE, "[]"))

    def get_sla_definitions(self) -> list[dict]:
        return json.loads(self._get_file_or_default(SLA_DEFINITIONS_FILE, "[]"))

    def push_integration(self, integration: Integration) -> None:
        """Writes an integration to the repo

        Args:
            integration: An integration object

        """
        integration.generate_readme(
            self.metadata.get_readme_addon("Integration", integration.identifier),
        )
        self.git.update_objects(
            integration.iter_files(self.api),
            base_path=f"{INTEGRATIONS_PATH}/{integration.identifier}",
        )

    def push_playbook(self, playbook: Workflow) -> None:
        """Writes a workflow to the repo

        Args:
            playbook: A playbook object

        """
        self._push_obj(
            playbook,
            playbook.name,
            "Playbook",
            f"{PLAYBOOKS_PATH}/{playbook.category}/{playbook.name}",
        )

    def push_block(self, block: Workflow, category: str | None = None) -> None:
        """Writes a block to the repo

        Args:
            block: A block object
            category: Optional category to override the block's own category

        """
        cat = category or block.category
        self._push_obj(
            block,
            block.name,
            "Block",
            f"{PLAYBOOKS_PATH}/{cat}/{block.name}",
        )

    def push_connector(self, connector: Connector) -> None:
        """Writes a connector instance to the repo

        Args:
            connector: A Connector object to write

        """
        self._push_obj(
            connector,
            connector.name,
            "Connector",
            f"{CONNECTORS_PATH}/{connector.integration}/{connector.name}",
        )

    def push_job(self, job: Job) -> None:
        """Writes a job instance to the repo

        Args:
            job: A Job object

        """
        self.git.update_objects(job.iter_files())

    def push_mapping(self, mapping: Mapping) -> None:
        """Writes mappings to the repo

        Args:
            mapping: A Mapping object to write

        """
        self._push_obj(
            mapping,
            mapping.integrationName,
            "Mappings",
            f"{MAPPINGS_PATH}/{mapping.integrationName}",
        )

    def push_visual_family(self, family: VisualFamily) -> None:
        """Writes a Visual Family to the repo

        Args:
            family: A VisualFamily object

        """
        self._push_obj(
            family,
            family.name,
            "Visual Family",
            f"{VISUAL_FAMILIES_PATH}/{family.name}",
        )

    def push_simulated_case(self, case_name: str, case: dict) -> None:
        self._push_file(f"{SIMULATED_CASES_PATH}/{case_name}.case", case)

    def push_integration_instances(self, integration_instances: list[dict]) -> None:
        self._push_file(INTEGRATION_INSTANCES_FILE, integration_instances)

    def push_dynamic_parameters(self, dynamic_parameters: list[dict]) -> None:
        self._push_file(DYNAMIC_PARAMS_FILES, dynamic_parameters)

    def push_environments(self, environments: list[dict]) -> None:
        self._push_file(ENVIRONMENTS_FILE, environments)

    def push_logo(self, logo: dict) -> None:
        self._push_file(LOGO_FILE, logo)

    def push_tags(self, tags: list[dict]) -> None:
        self._push_file(TAGS_FILE, tags)

    def push_stages(self, stages: list[dict]) -> None:
        self._push_file(STAGES_FILE, stages)

    def push_case_close_causes(self, close_causes: list[dict]) -> None:
        self._push_file(CASE_CLOSE_REASONS_FILE, close_causes)

    def push_case_titles(self, case_titles: list[dict]) -> None:
        self._push_file(CASE_TITLES_FILE, case_titles)

    def push_networks(self, networks: list[dict]) -> None:
        self._push_file(NETWORKS_FILE, networks)

    def push_domains(self, domains: list[dict]) -> None:
        self._push_file(DOMAINS_FILE, domains)

    def push_custom_lists(self, custom_lists: list[dict]) -> None:
        self._push_file(CUSTOM_LISTS_FILE, custom_lists)

    def push_email_templates(self, email_templates: list[dict]) -> None:
        self._push_file(EMAIL_TEMPLATES_FILE, email_templates)

    def push_denylists(self, denylists: list[dict]) -> None:
        self._push_file(DENYLIST_FILE, denylists)

    def push_sla_definitions(self, sla_definitions: list[dict]) -> None:
        self._push_file(SLA_DEFINITIONS_FILE, sla_definitions)

    def _get_file_or_default(self, path, default=None) -> Any:
        try:
            return self.git.get_file_contents_from_path(path)
        except KeyError:
            return default

    def _push_obj(self, content, content_name, content_type, path) -> None:
        content.generate_readme(
            self.metadata.get_readme_addon(content_type, content_name),
        )
        if self.deconstruct_playbooks and content_type in ("Playbook", "Block"):
            from .PlaybookYAMLConverter import PlaybookYAMLConverter
            existing_files = {}
            try:
                existing_files = {
                    pathlib.Path(f.path).name: f.content
                    for f in self.git.get_file_objects_from_path(path)
                }
            except Exception:
                pass
            deconstructed_files = PlaybookYAMLConverter.deconstruct_playbook(
                content.raw_data,
                existing_files,
            )
            deconstructed_files.append(File("README.md", content.readme))
            self.git.update_objects(deconstructed_files, base_path=path)
        else:
            self.git.update_objects(content.iter_files(), base_path=path)

    def _push_file(self, path: str, content) -> None:
        self.git.update_objects([File(path, self._json_encoder(content))])

    @staticmethod
    def _json_encoder(d: dict) -> str:
        return json.dumps(d, indent=4, sort_keys=True)
