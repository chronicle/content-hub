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

from ..core.definitions import Mapping
from ..core.GitSyncManager import GitSyncManager

SCRIPT_NAME = "Push Mappings"


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    commit_msg = siemplify.extract_job_param("Commit")
    source = siemplify.extract_job_param("Source")
    readme_addon = siemplify.extract_job_param("Readme Addon", input_type=str)

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)
        siemplify.LOGGER.info(f"Pushing mappings of {source}")
        all_records = gitsync.api.get_ontology_records(chronicle_soar=siemplify)
        records_integrations = {x.get("source") for x in all_records if x.get("source")}
        
        if source:
            matched_integration = None
            for integration in records_integrations:
                if integration.lower() == source.lower():
                    matched_integration = integration
                    break
            
            if matched_integration:
                records_integrations = {matched_integration}
            else:
                siemplify.LOGGER.warn(f"Source '{source}' not found in ontology records. Pushing nothing.")
                records_integrations = set()

        for integration in records_integrations:
            siemplify.LOGGER.info(f"Pushing {integration} mappings")
            if integration:
                records = [x for x in all_records if x["source"] == integration]
                if not records:
                    continue
                rules = []
                for record in records:
                    record["exampleEventFields"] = []
                    rule = gitsync.api.get_mapping_rules(
                        source=record["source"],
                        mr_id=record["id"],
                        product=record["product"],
                        event_name=record["eventName"],
                    )

                    def get_fields(rule):
                        """Extract iterable fields from either response format."""
                        if isinstance(rule, list):
                            return rule
                        if isinstance(rule, dict):
                            if "familyFields" in rule or "systemFields" in rule:
                                return rule.get("familyFields", []) + rule.get("systemFields", [])
                            elif "mapping_rules" in rule:
                                return rule.get("mapping_rules", [])
                            elif "mappingRules" in rule:
                                return rule.get("mappingRules", [])
                        return []

                    def get_mapping_rule(r, rule):
                        """Get the mappingRule dict from either format."""
                        if "mappingRule" in r:
                            return r["mappingRule"]
                        return r

                    for r in get_fields(rule):
                        mapping_rule = get_mapping_rule(r, rule)
                        rule_source = mapping_rule.get("source")
                        if not rule_source or rule_source.lower() == integration.lower():
                            if isinstance(rule, list):
                                rules.append(r)
                            else:
                                rules.append(rule)
                                break
                if readme_addon:
                    siemplify.LOGGER.info(
                        "Readme addon found - adding to GitSync metadata file (GitSync.json)",
                    )
                    gitsync.content.metadata.set_readme_addon("Mappings", integration, readme_addon)
                gitsync.content.push_mapping(Mapping(integration, records, rules))



        gitsync.commit_and_push(commit_msg)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    main()
