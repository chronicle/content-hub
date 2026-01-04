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

SCRIPT_NAME = "Pull Jobs"


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    job_names = [
        _f
        for _f in [
            x.strip()
            for x in siemplify.extract_job_param("Job Whitelist", " ").split(",")
        ]
        if _f
    ]

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        for job_name in job_names:
            siemplify.LOGGER.info(f"Pulling {job_name}")
            job_obj = gitsync.content.get_job(job_name)
            gitsync.install_job(job_obj)
            siemplify.LOGGER.info(f"Successfully pulled Job {job_obj.name}")

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
