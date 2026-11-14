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

from io import BytesIO

from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    ALL_ENVIRONMENTS_IDENTIFIER,
    AVAILABLE_CONTENT,
    IGNORED_INTEGRATIONS,
    IGNORED_JOBS,
    INTEGRATION_NAME,
)
from ..core.definitions import (
    Connector,
    Integration,
    Job,
    Mapping,
    VisualFamily,
    Workflow,
)
from ..core.GitSyncManager import GitSyncManager

SCRIPT_NAME = "Push Content"


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    commit_msg = siemplify.extract_job_param("Commit")
    commit_passwords = siemplify.extract_job_param("Commit Passwords", input_type=bool)

    # Features
    features = {}
    for feature in AVAILABLE_CONTENT:
        features[feature] = siemplify.extract_job_param(feature, input_type=bool)

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        # Integrations
        if features["Integrations"]:
            siemplify.LOGGER.info("========== Integrations ==========")
            for integration in [
                x
                for x in gitsync.api.get_ide_cards()
                if x.get("identifier") not in IGNORED_INTEGRATIONS
            ]:
                siemplify.LOGGER.info(f"Pushing {integration['identifier']}")
                integration_obj = Integration(
                    integration,
                    BytesIO(gitsync.api.export_package(integration["identifier"])),
                )
                try:
                    gitsync.content.push_integration(integration_obj)
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Couldn't upload {integration_obj.identifier}. ERROR: {e}",
                    )

        # Playbooks
        if features["Playbooks"]:
            siemplify.LOGGER.info("========== Playbooks ==========")
            for playbook in gitsync.api.get_playbooks():
                siemplify.LOGGER.info(f"Pushing {playbook['name']}")
                playbook = gitsync.api.get_playbook(playbook["identifier"])
                workflow = Workflow(playbook)
                workflow.update_instance_name_in_steps(gitsync.api, siemplify)
                gitsync.content.push_playbook(workflow)

        # Jobs
        if features["Jobs"]:
            siemplify.LOGGER.info("========== Jobs ==========")
            for job in [
                x
                for x in gitsync.api.get_jobs()
                if x.get("name") not in IGNORED_JOBS
                and x.get("integration") != INTEGRATION_NAME
                and not x.get("name").startswith("Cases Collector DB")
                and not x.get("name").startswith("Logs Collector")
            ]:
                siemplify.LOGGER.info(f"Pushing {job['name']}")
                gitsync.content.push_job(Job(job))

        # Connectors
        if features["Connectors"]:
            siemplify.LOGGER.info("========== Connectors ==========")
            for connector in gitsync.api.get_connectors():
                siemplify.LOGGER.info(f"Pushing {connector['displayName']}")
                gitsync.content.push_connector(Connector(connector))

        # Simulated Cases
        if features["Simulated Cases"]:
            siemplify.LOGGER.info("========== Simulated Cases ==========")
            for case in gitsync.api.get_simulated_cases():
                siemplify.LOGGER.info(f"Pushing {case}")
                gitsync.content.push_simulated_case(
                    case,
                    gitsync.api.export_simulated_case(case),
                )

        # Integration Instances
        if features["Integration Instances"]:
            siemplify.LOGGER.info("========== Integration Instances ==========")
            integration_instances = []
            for environment in gitsync.api.get_environment_names() + [
                ALL_ENVIRONMENTS_IDENTIFIER,
            ]:
                for instance in [
                    x
                    for x in gitsync.api.get_integrations_instances(environment)
                    if x.get("integrationIdentifier") not in IGNORED_INTEGRATIONS
                ]:
                    siemplify.LOGGER.info(f"Pushing {instance['instanceName']}")
                    settings = gitsync.api.get_integration_instance_settings(
                        instance["identifier"],
                    )
                    for sett in settings:  # Remove Agent Identifiers from settings - should be created separately
                        if sett["propertyName"] == "AgentIdentifier":
                            sett["value"] = None
                        sett["creationTimeUnixTimeInMs"] = 0
                        sett["modificationTimeUnixTimeInMs"] = 0
                    if commit_passwords:
                        try:
                            secrets = siemplify.get_configuration(
                                instance["identifier"],
                            )
                            for prop in settings:
                                if prop["propertyType"] == 3:
                                    try:
                                        prop["value"] = secrets[prop["propertyName"]]
                                    except KeyError:
                                        siemplify.LOGGER.warn(
                                            f"{instance['instanceName']} was updated with new "
                                            f"parameters but they weren't configured.",
                                        )
                        except Exception:
                            siemplify.LOGGER.warn(
                                f"{instance['identifier']} is not configured. Skipping passwords",
                            )

                    integration_instances.append(
                        {
                            "environment": environment,
                            "integrationIdentifier": instance["integrationIdentifier"],
                            "settings": {
                                "instanceDescription": instance["instanceDescription"],
                                "instanceName": instance["instanceName"],
                                "settings": settings,
                            },
                        },
                    )
            gitsync.content.push_integration_instances(integration_instances)

        # Ontology - Visual Families
        if features["Visual Families"]:
            siemplify.LOGGER.info("========== Visual Families ==========")
            for visualFamily in gitsync.api.get_custom_families():
                siemplify.LOGGER.info(f"Pushing {visualFamily['family']}")
                gitsync.content.push_visual_family(
                    VisualFamily(gitsync.api.get_custom_family(visualFamily["id"])),
                )

        # Ontology - Mappings
        if features["Mappings"]:
            siemplify.LOGGER.info("========== Mappings ==========")
            all_records = gitsync.api.get_ontology_records()
            records_integrations = set([x["source"] for x in all_records])
            for integration in records_integrations:
                siemplify.LOGGER.info(f"Pushing {integration} mappings")
                if integration:
                    records = [x for x in all_records if x["source"] == integration]
                    if not records:
                        continue
                    rules = []
                    for record in records:
                        record["exampleEventFields"] = []  # remove event assets
                        rule = gitsync.api.get_mapping_rules(
                            record["source"],
                            record["product"],
                            record["eventName"],
                        )
                        for r in rule["familyFields"] + rule["systemFields"]:
                            # remove bad rules with no source
                            if (
                                r["mappingRule"]["source"]
                                and r["mappingRule"]["source"].lower()
                                == integration.lower()
                            ):
                                rules.append(rule)
                                break

                    gitsync.content.push_mapping(Mapping(integration, records, rules))

        # Other settings
        siemplify.LOGGER.info("========== Settings ==========")
        if features["Environments"]:
            siemplify.LOGGER.info("Pushing environments")
            environments = gitsync.api.get_environments()
            for environment in environments:
                environment["id"] = 0
            gitsync.content.push_environments(environments)

        if features["Dynamic Parameters"]:
            siemplify.LOGGER.info("Pushing dynamic parameters")
            gitsync.content.push_dynamic_parameters(
                gitsync.api.get_env_dynamic_parameters(),
            )

        if features["Logo"]:
            siemplify.LOGGER.info("Pushing logo")
            logo = gitsync.api.get_logo()
            if logo["imageBase64"]:
                # A custom logo is configured.
                logo["imageBase64"] = "data:image/png;base64," + logo["imageBase64"]
            gitsync.content.push_logo(logo)

        if features["Case Tags"]:
            siemplify.LOGGER.info("Pushing case tags")
            gitsync.content.push_tags(gitsync.api.get_case_tags())

        if features["Case Stages"]:
            siemplify.LOGGER.info("Pushing case stages")
            gitsync.content.push_stages(gitsync.api.get_case_stages())

        if features["Case Title Settings"]:
            siemplify.LOGGER.info("Pushing case title settings")
            gitsync.content.push_case_titles(gitsync.api.get_case_title_settings())

        if features["Case Close Reasons"]:
            siemplify.LOGGER.info("Pushing case close reasons")
            gitsync.content.push_case_close_causes(gitsync.api.get_close_reasons())

        if features["Networks"]:
            siemplify.LOGGER.info("Pushing networks")
            gitsync.content.push_networks(gitsync.api.get_networks())

        if features["Domains"]:
            siemplify.LOGGER.info("Pushing domains")
            gitsync.content.push_domains(gitsync.api.get_domains())

        if features["Custom Lists"]:
            siemplify.LOGGER.info("Pushing custom lists")
            gitsync.content.push_custom_lists(gitsync.api.get_custom_lists())

        if features["Email Templates"]:
            siemplify.LOGGER.info("Pushing email templates")
            gitsync.content.push_email_templates(gitsync.api.get_email_templates())

        if features["Blacklists"]:
            siemplify.LOGGER.info("Pushing denylists")
            gitsync.content.push_denylists(gitsync.api.get_denylists())

        if features["SLA Records"]:
            siemplify.LOGGER.info("Pushing SLA records")
            gitsync.content.push_sla_definitions(gitsync.api.get_sla_records())

        siemplify.LOGGER.info("Done! uploading everything to git")
        gitsync.commit_and_push(commit_msg)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
