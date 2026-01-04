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

SCRIPT_NAME = "Push Simulated Cases"


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    commit_msg = siemplify.extract_job_param("Commit")
    cases = [
        _f
        for _f in [
            x.strip()
            for x in siemplify.extract_job_param("Simulated Cases", " ").split(",")
        ]
        if _f
    ]

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        for case_name in gitsync.api.get_simulated_cases():
            if case_name in cases:
                siemplify.LOGGER.info(f"Pushing simulated case {case_name}")
                gitsync.content.push_simulated_case(
                    case_name,
                    gitsync.api.export_simulated_case(case_name),
                )

        gitsync.commit_and_push(commit_msg)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    main()
