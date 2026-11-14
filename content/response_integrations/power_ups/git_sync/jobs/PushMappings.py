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
        records = [
            x
            for x in gitsync.api.get_ontology_records()
            if x.get("source").lower() == source.lower()
        ]
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
                    and r["mappingRule"]["source"].lower() == source.lower()
                ):
                    rules.append(rule)
                    break

        if readme_addon:
            siemplify.LOGGER.info(
                "Readme addon found - adding to GitSync metadata file (GitSync.json)",
            )
            gitsync.content.metadata.set_readme_addon("Mappings", source, readme_addon)

        gitsync.content.push_mapping(Mapping(source, records, rules))
        gitsync.commit_and_push(commit_msg)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    main()
