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

from ..core.GitSyncManager import GitSyncManager

SCRIPT_NAME = "Pull Connector"


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    connector_name = siemplify.extract_job_param("Connector Name")
    include_vf = siemplify.extract_job_param("Include Visual Families", input_type=bool)
    include_mappings = siemplify.extract_job_param("Include Mappings", input_type=bool)

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        connector = gitsync.content.get_connector(connector_name)
        if connector:
            siemplify.LOGGER.info(f"Installing Connector {connector_name}")
            gitsync.install_connector(connector)
            siemplify.LOGGER.info(
                f"Connector {connector_name} - successfully installed",
            )

            if include_vf or include_mappings:
                mappings = gitsync.content.get_mapping(connector.integration)
                if mappings:
                    installed_visual_families = [
                        x.get("family") for x in gitsync.api.get_custom_families(True)
                    ]
                    visual_families = set(
                        [
                            x.get("familyName")
                            for x in mappings.records
                            if x.get("familyName") not in installed_visual_families
                        ],
                    )

                    if include_vf:
                        siemplify.LOGGER.info("Installing Visual Families")
                        for vf in visual_families:
                            siemplify.LOGGER.info(f"Pulling visual family {vf}")
                            gitsync.api.add_custom_family(
                                gitsync.content.get_visual_family(vf).raw_data,
                            )

                    if include_mappings:
                        siemplify.LOGGER.info("Installing Mappings")
                        gitsync.install_mappings(mappings)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
