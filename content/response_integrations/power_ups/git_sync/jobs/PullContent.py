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

from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.data_models import CaseTag
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

        if features["Dynamic Parameters"]:
            siemplify.LOGGER.info(
                "========== Environment Dynamic Parameters ==========",
            )
            current_parameters = gitsync.api.get_env_dynamic_parameters(chronicle_soar=siemplify)
            for dynParam in gitsync.content.get_dynamic_parameters():
                siemplify.LOGGER.info(
                    f"Adding dynamic parameter {dynParam.get('name')}",
                )
                gitsync.api.add_dynamic_env_param(
                    siemplify,
                    id=dynParam.get("id", 0),
                    name=dynParam.get("name", ""),
                    value=current_parameters.get("value", ""),
                    type=current_parameters.get("type", ""),
                    default_value=current_parameters.get("defaultValue", ""),
                    optional_json=current_parameters,
                )

        if features["Environments"]:
            siemplify.LOGGER.info("========== Environments ==========")
            all_environments_names = gitsync.api.get_environment_names(chronicle_soar=siemplify)
            for environment in gitsync.content.get_environments():
                if environment.get("name") in all_environments_names:
                    existing_env_id = next(
                        x._id
                        for x in gitsync.api.get_environments(siemplify)
                        if x.name == environment.get("name")
                    )
                    environment["id"] = existing_env_id
                    siemplify.LOGGER.info(
                        f"Updating environment {environment.get('name')}",
                    )
                else:
                    siemplify.LOGGER.info(
                        f"Adding environment {environment.get('name')}",
                    )

                gitsync.api.import_environment(siemplify, environment)

        if features["Integrations"]:
            siemplify.LOGGER.info("========== Integrations ==========")
            for integration in gitsync.content.get_integrations():
                gitsync.install_integration(integration)
            gitsync.clear_cache()

        if features["Integration Instances"]:
            siemplify.LOGGER.info("========== Integration instances ==========")
            current_instances = gitsync.api.get_integrations_instances(chronicle_soar=siemplify, environment=ALL_ENVIRONMENTS_IDENTIFIER)
            for env in gitsync.api.get_environment_names(chronicle_soar=siemplify):
                current_instances.extend(gitsync.api.get_integrations_instances(chronicle_soar=siemplify, environment=env))
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
                        instance_to_update = current
                    else:
                        siemplify.LOGGER.info(
                            f"Installing {instance['settings']['instanceName']}",
                        )
                        instance_to_update = gitsync.api.create_integrations_instance(
                            siemplify,
                            instance["integrationIdentifier"],
                            instance["environment"],
                        )
                    for i in instance["settings"]["settings"]:
                        i["integrationInstance"] = instance_to_update.identifier

                    gitsync.api.save_integration_instance_settings(
                        siemplify,
                        instance_to_update.identifier,
                        instance["settings"],
                        instance["environment"],
                    )

        if features["Playbooks"]:
            siemplify.LOGGER.info("========== Playbooks ==========")
            gitsync.install_workflows(list(gitsync.content.get_playbooks()))

        if features["Connectors"]:
            siemplify.LOGGER.info("========== Connectors ==========")
            for connector in gitsync.content.get_connectors():
                siemplify.LOGGER.info(f"Installing {connector.name}")
                gitsync.install_connector(connector)

        if features["Jobs"]:
            siemplify.LOGGER.info("========== Jobs ==========")
            for job in gitsync.content.get_jobs():
                siemplify.LOGGER.info(f"Installing {job.name}")
                gitsync.install_job(job)

        if features["Simulated Cases"]:
            siemplify.LOGGER.info("Installing Simulated Cases")
            for case in gitsync.content.get_simulated_cases():
                gitsync.api.import_simulated_case(siemplify, case)

        if features["Case Tags"]:
            siemplify.LOGGER.info("Installing tags")
            current_tags = gitsync.api.get_case_tags(chronicle_soar=siemplify)
            for tag in gitsync.content.get_tags():
                current_tag = id_validator(tag, "name", "id", current_tags)
                current_tag = (
                    CaseTag.from_json(current_tag).to_json_1p()
                    if platform_supports_1p_api()
                    else CaseTag.from_json(current_tag).to_json_legacy()
                )

                gitsync.api.add_case_tag(siemplify, current_tag)

        if features["Case Stages"]:
            siemplify.LOGGER.info("Installing stages")
            current_stages = gitsync.api.get_case_stages(chronicle_soar=siemplify)
            for stage in gitsync.content.get_stages():
                gitsync.api.add_case_stage(
                    siemplify,
                    id_validator(stage, "name", "id", current_stages),
                )

        if features["Case Close Reasons"]:
            siemplify.LOGGER.info("Installing case close reasons")
            current_causes = gitsync.api.get_close_reasons(chronicle_soar=siemplify)
            for cause in gitsync.content.get_case_close_causes():
                gitsync.api.add_close_reason(
                    siemplify,
                    id_validator(
                        cause,
                        ("rootCause", "forCloseReason"),
                        "id",
                        current_causes,
                    ),
                )

        if features["Case Title Settings"]:
            case_title_settings = gitsync.content.get_case_titles()
            if case_title_settings:
                siemplify.LOGGER.info("Installing case title settings")
                gitsync.api.save_case_title_settings(case_title_settings)

        if features["Visual Families"]:
            siemplify.LOGGER.info("Installing visual families")
            current_vfs = gitsync.api.get_custom_families(chronicle_soar=siemplify)
            for family in gitsync.content.get_visual_families():
                gitsync.api.add_custom_family(
                    {
                        "visualFamilyDataModel": (
                            id_validator(family.raw_data, "family", "id", current_vfs)
                        ),
                    },
                )

        if features["Mappings"]:
            siemplify.LOGGER.info("Installing mappings")
            for mapping in gitsync.content.get_mappings():
                gitsync.install_mappings(mapping)

        if features["Networks"]:
            siemplify.LOGGER.info("Installing networks")
            current_networks = gitsync.api.get_networks(chronicle_soar=siemplify)
            for network in gitsync.content.get_networks():
                gitsync.api.update_network(
                    siemplify,
                    id_validator(network, "name", "id", current_networks),
                )

        if features["Domains"]:
            siemplify.LOGGER.info("Installing domains")
            current_domains = gitsync.api.get_domains(chronicle_soar=siemplify)
            for domain in gitsync.content.get_domains():
                gitsync.api.update_domain(
                    siemplify,
                    id_validator(domain, "domain", "id", current_domains),
                )

        if features["Custom Lists"]:
            siemplify.LOGGER.info("Installing custom lists")
            for lst in gitsync.content.get_custom_lists():
                gitsync.api.update_custom_list(siemplify, lst)

        if features["Email Templates"]:
            siemplify.LOGGER.info("Installing email templates")
            current_templates = gitsync.api.get_email_templates(chronicle_soar=siemplify)
            for template in gitsync.content.get_email_templates():
                gitsync.api.add_email_template(
                    id_validator(template, "name", "id", current_templates),
                )

        if features["Blacklists"]:
            siemplify.LOGGER.info("Installing denylists")
            for bl in gitsync.content.get_denylists():
                gitsync.api.update_denylist(siemplify, bl)

        if features["SLA Records"]:
            siemplify.LOGGER.info("Installing SLA definition")
            for definition in gitsync.content.get_sla_definitions():
                gitsync.api.update_sla_record(siemplify, definition)

        if features["Logo"]:
            if not gitsync.content.get_logo():
                siemplify.LOGGER.info("Logo not found. Skipping")
            else:
                siemplify.LOGGER.info("Installing Logo")
                gitsync.api.update_logo(gitsync.content.get_logo())

        siemplify.LOGGER.info("Finished Successfully")

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
