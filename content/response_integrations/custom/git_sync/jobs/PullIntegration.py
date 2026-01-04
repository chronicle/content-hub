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

SCRIPT_NAME = "Pull Integration"


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    pull_allowlist = [
        _f
        for _f in [
            x.strip()
            for x in siemplify.extract_job_param("Install Whitelist", " ").split(",")
        ]
        if _f
    ]

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        for integration_name in pull_allowlist:
            siemplify.LOGGER.info(f"Pulling Integration: {integration_name}")
            integration = gitsync.content.get_integration(integration_name)
            if integration:
                siemplify.LOGGER.info(f"Installing {integration.identifier}")
                gitsync.install_integration(integration)
                siemplify.LOGGER.info(
                    f"Successfully installed {integration.identifier}",
                )
            else:
                siemplify.LOGGER.info(f"Couldn't find {integration_name} in the repo")

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
