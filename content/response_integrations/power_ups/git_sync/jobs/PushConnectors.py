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

from ..core.definitions import Connector, Mapping, VisualFamily
from ..core.GitSyncManager import GitSyncManager

SCRIPT_NAME = "Push Connector"


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    commit_msg = siemplify.extract_job_param("Commit")
    connector_names = [
        _f
        for _f in [
            x.strip() for x in siemplify.extract_job_param("Connectors", " ").split(",")
        ]
        if _f
    ]
    include_vf = siemplify.extract_job_param("Include Visual Families", input_type=bool)
    include_mappings = siemplify.extract_job_param("Include Mappings", input_type=bool)
    readme_addon = siemplify.extract_job_param("Readme Addon", input_type=str)

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        for connector in gitsync.api.get_connectors(chronicle_soar=siemplify):
            if connector.get("displayName") in connector_names:
                siemplify.LOGGER.info(f"Pushing {connector.get('displayName')}")
                if readme_addon:
                    siemplify.LOGGER.info(
                        "Readme addon found - adding to GitSync metadata file (GitSync.json)",
                    )
                    gitsync.content.metadata.set_readme_addon(
                        "Connector",
                        connector.get("displayName"),
                        readme_addon,
                    )

                gitsync.content.push_connector(Connector(connector))
                siemplify.LOGGER.info(
                    f"Successfully pushed {connector.get('displayName')}",
                )

                if include_mappings or include_vf:
                    integration_name = connector.get("integration")
                    records = [
                        x
                        for x in gitsync.api.get_ontology_records(chronicle_soar=siemplify)
                        if x.get("source") == integration_name
                    ]
                    visual_families = set([x.get("familyName") for x in records])
                    if include_mappings:
                        rules = []
                        for record in records:
                            record["exampleEventFields"] = []  # remove event assets
                            rule = gitsync.api.get_mapping_rules(
                                source=record["source"],
                                mr_id=record["id"], 
                                product=record["product"],
                                event_name=record["eventName"],
                            )
                            def get_fields(rule):
                                """Extract iterable fields from either response format."""
                                if "familyFields" in rule or "systemFields" in rule:
                                    return rule.get("familyFields", []) + rule.get("systemFields", [])
                                elif "mapping_rules" in rule:
                                    return rule.get("mapping_rules", [])
                                return []

                            def get_mapping_rule(r, rule):
                                """Get the mappingRule dict from either format."""
                                if "mappingRule" in r:
                                    return r["mappingRule"]
                                return r

                            for r in get_fields(rule):
                                mapping_rule = get_mapping_rule(r, rule)
                                source = mapping_rule.get("source")
                                if source and source.lower() == integration_name.lower():
                                    rules.append(rule)
                                    break
                        if not records and not rules:
                            siemplify.LOGGER.info(
                                f"{integration_name} mappings don't exist. Skipping",
                            )
                        else:
                            siemplify.LOGGER.info(
                                f"Pushing {integration_name} mappings",
                            )
                            gitsync.content.push_mapping(
                                Mapping(integration_name, records, rules),
                            )

                    if include_vf:
                        for visualFamily in gitsync.api.get_custom_families(chronicle_soar=siemplify):
                            if visualFamily["family"] in visual_families:
                                siemplify.LOGGER.info(
                                    f"Pushing Visual Family - {visualFamily['family']}",
                                )
                                gitsync.content.push_visual_family(
                                    VisualFamily(
                                        gitsync.api.get_custom_family(
                                            chronicle_soar=siemplify,
                                            family_id=visualFamily["id"],
                                        ),
                                    ),
                                )

        gitsync.commit_and_push(commit_msg)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    main()
