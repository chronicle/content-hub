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

from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.data_models import (
    BlockRecord,
    CaseTag,
    CaseStage,
    Domain,
    CustomList,
    Network,
    CaseCloseReasons,
    SlaDefinition,
    Environment,
    SimulatedCases,
)

from TIPCommon.utils import platform_supports_1p_api

from ..core.constants import (
    ALL_ENVIRONMENTS_IDENTIFIER,
    AVAILABLE_CONTENT,
    IGNORED_INTEGRATIONS,
)
from ..core.GitSyncManager import GitSyncManager

SCRIPT_NAME = "Pull Content"


def id_validator(resource, fields_to_compare, id_field, current_state):
    resource[id_field] = 0
    if isinstance(fields_to_compare, str):
        fields_to_compare = [fields_to_compare]
    current = next(
        (x for x in current_state if all(x[y] == resource[y] for y in fields_to_compare)),
        None,
    )
    if current:
        resource[id_field] = current[id_field]
    return resource


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    features = {}
    for feature in AVAILABLE_CONTENT:
        features[feature] = siemplify.extract_job_param(feature, input_type=bool)

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        if features["Dynamic Parameters"]: # 20 jan
            siemplify.LOGGER.info("======== Environment Dynamic Parameters ========")

            # current_parameters = gitsync.api.get_env_dynamic_parameters(chronicle_soar=siemplify)

            # current_by_name = {p.get("name"): p for p in current_parameters}

            for dyn_param in gitsync.content.get_dynamic_parameters():
                name = dyn_param.get("name")
                siemplify.LOGGER.info(f"Adding dynamic parameter {name}")
                gitsync.api.add_dynamic_env_param(dyn_param)

        if features["Environments"]:
            siemplify.LOGGER.info("========== Environments ==========")

            all_envs = gitsync.api.get_environments(siemplify)

            for environment in gitsync.content.get_environments():
                env_name = environment.get("name")

                existing_env = next(
                    (x for x in all_envs if x.name == env_name),
                    None,
                )

                if existing_env:
                    environment["id"] = existing_env.identifier
                    environment["name"] = existing_env.name  # 🔒 preserve immutable name
                    siemplify.LOGGER.info(f"Updating environment {env_name}")
                else:
                    siemplify.LOGGER.info(f"Adding environment {env_name}")

                payload = (
                    Environment.from_json(environment).to_1p()
                    if platform_supports_1p_api()
                    else Environment.from_json(environment).to_legacy()
                )

                gitsync.api.import_environment(siemplify, payload)

        if features["Integrations"]:
            siemplify.LOGGER.info("========== Integrations ==========")
            for integration in gitsync.content.get_integrations():
                gitsync.install_integration(integration)
            gitsync.clear_cache()

        if features["Integration Instances"]:
            siemplify.LOGGER.info("========== Integration instances ==========")

            current_instances = gitsync.api.get_integrations_instances(
                chronicle_soar=siemplify, environment=ALL_ENVIRONMENTS_IDENTIFIER
            )

            for env in gitsync.api.get_environment_names(chronicle_soar=siemplify):
                current_instances.extend(
                    gitsync.api.get_integrations_instances(
                        chronicle_soar=siemplify, environment=env
                    )
                )

            for instance in gitsync.content.get_integration_instances():
                if instance["integrationIdentifier"] not in IGNORED_INTEGRATIONS:

                    current = next(
                        (
                            x
                            for x in current_instances
                            if x.environment_identifier == instance["environment"]
                            and x.integration_identifier == instance["integrationIdentifier"]
                            and x.instance_name == instance["settings"]["instanceName"]
                        ),
                        None,
                    )

                    if current:
                        siemplify.LOGGER.info(
                            f"Updating {instance['settings']['instanceName']}",
                        )
                        instance_to_update = current.to_json()
                    else:
                        siemplify.LOGGER.info(
                            f"Installing {instance['settings']['instanceName']}",
                        )
                        instance_to_update = gitsync.api.create_integrations_instance(
                            siemplify,
                            instance["integrationIdentifier"],
                            instance["environment"],
                        )

                    instance_identifier = instance_to_update.get("identifier")

                    for setting in instance["settings"]["settings"]:
                        setting["integrationInstance"] = instance_identifier

                    instance["settings"]["instanceIdentifier"] = instance_identifier

                    gitsync.api.save_integration_instance_settings(
                        instance_identifier=instance_identifier,
                        env=instance["environment"],
                        settings=instance["settings"],
                    )

        if features["Playbooks"]:
            siemplify.LOGGER.info("========== Playbooks ==========")
            gitsync.install_workflows(list(gitsync.content.get_playbooks()))

        if features["Connectors"]:
            siemplify.LOGGER.info("========== Connectors ==========")
            existing_connectors = gitsync.api.get_connectors(chronicle_soar=siemplify) 
            for connector in gitsync.content.get_connectors():# Assuming this API exists
                
                    is_duplicate = any(
                        c.get("name") or c.get("displayName")  == connector.name and c.get("environment") == connector.environment
                        for c in existing_connectors
                    )

                    if is_duplicate:
                        siemplify.LOGGER.info(f"Connector {connector.name} already exists in {connector.environment}. Updating.")
                        continue
                    siemplify.LOGGER.info(f"Installing {connector.name}")
                    gitsync.install_connector(connector)


        if features["Jobs"]:
            siemplify.LOGGER.info("========== Jobs ==========")
            for job in gitsync.content.get_jobs():
                siemplify.LOGGER.info(f"Installing {job.name}")
                gitsync.install_job(job)

        if features["Simulated Cases"]:
            siemplify.LOGGER.info("Installing Simulated Cases")

            for raw_payload in gitsync.content.get_simulated_cases():
                normalized_payload = (
                    SimulatedCases
                    .from_legacy_or_1p(raw_payload)
                    .to_1p()
                )

                gitsync.api.import_simulated_case(
                    siemplify,
                    normalized_payload,
                )

        if features["Case Tags"]:
            siemplify.LOGGER.info("Installing tags")
            current_tags = gitsync.api.get_case_tags(chronicle_soar=siemplify)
            for tag in gitsync.content.get_tags():
                current_tag = id_validator(tag, "name", "id", current_tags)
                current_tag = (
                    CaseTag.from_json(current_tag).to_json_1p()
                    if platform_supports_1p_api()
                    else CaseTag.from_json(current_tag).to_json()
                )

                gitsync.api.add_case_tag(siemplify, current_tag)

        if features["Case Stages"]:
            siemplify.LOGGER.info("Installing stages")
            current_stages = gitsync.api.get_case_stages(chronicle_soar=siemplify)
            for stage in gitsync.content.get_stages():
                current_stage = id_validator(stage, "name", "id", current_stages)
                current_stage = (
                    CaseStage.from_legacy_or_1p(current_stage).to_1p()
                    if platform_supports_1p_api()
                    else CaseStage.from_legacy_or_1p(current_stage).to_legacy()
                )

                gitsync.api.add_case_stage(siemplify, current_stage)

        if features["Case Close Reasons"]:
            siemplify.LOGGER.info("Installing case close reasons")
            current_causes = gitsync.api.get_close_reasons(chronicle_soar=siemplify)
            for cause in gitsync.content.get_case_close_causes():
                current_cause= id_validator(
                        cause,
                        "rootCause",
                        "id",
                        current_causes,
                    )
                current_cause = (
                    CaseCloseReasons.from_legacy_or_1p(current_cause).to_1p()
                    if platform_supports_1p_api()
                    else CaseCloseReasons.from_legacy_or_1p(current_cause).to_legacy()
                )

                if "forCloseReason" in cause: # QA fixes
                    current_cause["forCloseReason"] = cause["forCloseReason"]
                gitsync.api.add_close_reason(siemplify, current_cause)


        if features["Case Title Settings"]:
            case_title_settings = gitsync.content.get_case_titles()
            if case_title_settings:
                siemplify.LOGGER.info("Installing case title settings")
                siemplify.LOGGER.info(f"===================={case_title_settings}====================")

                if isinstance(case_title_settings, dict) and "items" in case_title_settings:
                    for item in case_title_settings.get("items", []):
                        val = item.get("value")
                        normalized_value = val if val and val.strip() else "Null"
                        
                        gitsync.api.save_case_title_settings(
                            name=item.get("name"),
                            display_name=item.get("displayName"),
                            value=normalized_value,
                            type_=item.get("type", 2),
                            settings=None
                        )

                elif isinstance(case_title_settings, list):
                    gitsync.api.save_case_title_settings(
                        name=None,
                        display_name=None,
                        value=None,
                        type_=None,
                        settings=case_title_settings
                )

        if features["Visual Families"]:
            siemplify.LOGGER.info("Installing visual families")
            current_vfs = gitsync.api.get_custom_families(chronicle_soar=siemplify)
            all_records = gitsync.api.get_ontology_records(chronicle_soar=siemplify) #vf
            valid_record_id = all_records[0].get("id") if all_records else None #vf
            for family in gitsync.content.get_visual_families():
                gitsync.api.add_custom_family(
                    {
                        "visualFamilyDataModel": (
                            id_validator(family.raw_data, "family", "id", current_vfs)
                        ),
                    },
                    valid_record_id, #vf
                )

        if features["Mappings"]:
            siemplify.LOGGER.info("Installing mappings")
            for mapping in gitsync.content.get_mappings():
                gitsync.install_mappings(mapping)

        if features["Networks"]:
            siemplify.LOGGER.info("Installing networks")
            current_networks = gitsync.api.get_networks(chronicle_soar=siemplify)
            for network in gitsync.content.get_networks():
                current_network = id_validator(network, "name", "id", current_networks)
                current_network = (
                    Network.from_legacy_or_1p(current_network).to_1p()
                    if platform_supports_1p_api()
                    else Network.from_legacy_or_1p(current_network).to_legacy()
                )

                gitsync.api.update_network(siemplify, current_network)

        if features["Domains"]:
            siemplify.LOGGER.info("Installing domains")
            current_domains = gitsync.api.get_domains(chronicle_soar=siemplify)
            for domain in gitsync.content.get_domains():
                current_domain = id_validator(domain, "domain", "id", current_domains)
                current_domain = (
                    Domain.from_legacy_or_1p(current_domain).to_1p()
                    if platform_supports_1p_api()
                    else Domain.from_legacy_or_1p(current_domain).to_legacy()
                )

                gitsync.api.update_domain(siemplify, current_domain)

        if features["Custom Lists"]:
            siemplify.LOGGER.info("Installing custom lists")
            current_lsts = gitsync.api.get_custom_lists(chronicle_soar=siemplify)
            for lst in gitsync.content.get_custom_lists():
                current_lst = id_validator(lst, "category", "id", current_lsts)
                current_lst = (
                    CustomList.from_legacy_or_1p(current_lst).to_1p()
                    if platform_supports_1p_api()
                    else CustomList.from_legacy_or_1p(current_lst).to_legacy()
                )

                gitsync.api.update_custom_list(siemplify, current_lst)

        if features["Email Templates"]:
            siemplify.LOGGER.info("Installing email templates")
            current_templates = gitsync.api.get_email_templates(chronicle_soar=siemplify)
            for template in gitsync.content.get_email_templates():
                validated_template = id_validator(template, "name", "id", current_templates)
                name_to_check = template.get("displayName") or template.get("name")
                if any((t.get("displayName") == name_to_check or t.get("name") == name_to_check) for t in current_templates):
                    siemplify.LOGGER.info(f"Email template \"{name_to_check}\" already exists. Skipping.")
                    continue
                
                gitsync.api.add_email_template(validated_template)

        if features["Blacklists"]:
            siemplify.LOGGER.info("Installing denylists")
            denylists = gitsync.content.get_denylists()
            if isinstance(denylists, str):
                try:
                    denylists = json.loads(denylists)
                except Exception:
                    siemplify.LOGGER.warn(f"Failed to parse denylists string as JSON: {denylists}")
                    denylists = []

            if isinstance(denylists, dict):
                denylists = denylists.get("soar_block_entities") or denylists.get("items") or denylists.get("soarBlockEntities") or []

            for definition in denylists:
                if isinstance(definition, str):
                    try:
                        definition = json.loads(definition)
                    except Exception:
                        siemplify.LOGGER.warn(f"Skipping invalid denylist definition (not valid JSON): {definition}")
                        continue

                if not isinstance(definition, dict):
                    siemplify.LOGGER.warn(f"Skipping invalid denylist definition (expected dict, got {type(definition)}): {definition}")
                    continue

                action_val = definition.get("action") or definition.get("Action")
                envs_json_val = definition.get("environmentsJson") or definition.get("EnvironmentsJson")

                definition = (
                    BlockRecord.from_legacy_or_1p(definition).to_1p()
                    if platform_supports_1p_api()
                    else BlockRecord.from_legacy_or_1p(definition).to_legacy()
                )

                if action_val:
                    definition["action"] = action_val
                if envs_json_val:
                    definition["environmentsJson"] = envs_json_val
                gitsync.api.update_denylist(siemplify, definition)
        
        if features["SLA Records"]:
            siemplify.LOGGER.info("Installing SLA definition")
            current_sla_records = gitsync.api.get_sla_records(chronicle_soar=siemplify)
            for definition in gitsync.content.get_sla_definitions():
                if not isinstance(definition, dict):
                    continue

                def_type = definition.get("slaType") or definition.get("Type")
                def_val = definition.get("slaTypeValue") or definition.get("TypeValue")
                def_envs = definition.get("environments") or ([definition.get("environment")] if definition.get("environment") else []) or ([definition.get("Environment")] if definition.get("Environment") else [])
                def_envs = [e for e in def_envs if e]
                
                is_duplicate = False
                for c in current_sla_records:
                    if not isinstance(c, dict):
                        continue
                    c_type = c.get("slaType") or c.get("Type")
                    c_val = c.get("slaTypeValue") or c.get("TypeValue")
                    c_envs = c.get("environments") or ([c.get("environment")] if c.get("environment") else []) or ([c.get("Environment")] if c.get("Environment") else [])
                    c_envs = [e for e in c_envs if e]
                    
                    if c_type == def_type and c_val == def_val:
                        if any(e in def_envs for e in c_envs):
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    siemplify.LOGGER.info(f"SLA Record of type \"{def_type}\" (\"{def_val}\") already exists for overlapping environments. Skipping.")
                    continue

                try:
                    gitsync.api.update_sla_record(siemplify, definition)
                except Exception as e:
                    siemplify.LOGGER.error(f"Failed to update SLA definition: {e}")

        if features["Logo"]:
            logo_data = gitsync.content.get_logo()
            if not logo_data:
                siemplify.LOGGER.info("Logo not found. Skipping")
            else:
                siemplify.LOGGER.info("Installing Logo")

                if "items" in logo_data:

                    for item in logo_data.get("items", []):
                        
                        if "value" not in item:
                            item["value"] = "True"
                    
                        payload = item
                        gitsync.api.update_logo(payload)

                    siemplify.LOGGER.info("Finished Successfully")
                else:
                    gitsync.api.update_logo(gitsync.content.get_logo())
                siemplify.LOGGER.info("Finished Successfully")
        

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
