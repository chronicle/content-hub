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

SCRIPT_NAME = "Pull Custom Family"


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    family_name = siemplify.extract_job_param("Family Name")

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        siemplify.LOGGER.info(f"Pulling {family_name}")
        family = gitsync.content.get_visual_family(family_name)
        if family:
            gitsync.api.add_custom_family(family.raw_data)
            siemplify.LOGGER.info(f"Successfully pulled {family_name}")
        else:
            siemplify.LOGGER.info(f"Family {family_name} not found")

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
