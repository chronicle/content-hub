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

from ..core.constants import IGNORED_JOBS, INTEGRATION_NAME
from ..core.definitions import Job
from ..core.GitSyncManager import GitSyncManager

SCRIPT_NAME = "Push Job"


def create_root_readme(gitsync: GitSyncManager):
    jobs = []
    for job in gitsync.content.get_jobs():
        job.generate_readme(gitsync.content.metadata.get_readme_addon("Job", job.name))
        jobs.append(job)

    readme = "".join([x.readme for x in jobs])
    gitsync.update_readme(readme, "Jobs")


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    commit_msg = siemplify.extract_job_param("Commit")
    jobs = list(
        [
            _f
            for _f in [
                x.strip()
                for x in siemplify.extract_job_param("Job Whitelist", " ").split(",")
            ]
            if _f
        ],
    )
    readme_addon = siemplify.extract_job_param("Readme Addon", input_type=str)

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        for job in gitsync.api.get_jobs(chronicle_soar=siemplify):
            if (
                job.get("displayName", job.get("name")) in jobs
                and job.get("displayName", job.get("name")) not in IGNORED_JOBS
                and job.get("integration") != INTEGRATION_NAME
            ):
                siemplify.LOGGER.info(f"Pushing {job.get("displayName", job.get("name"))}")
                job = Job(job)
                if readme_addon:
                    siemplify.LOGGER.info(
                        "Readme addon found - adding to GitSync metadata file (GitSync.json)",
                    )
                    gitsync.content.metadata.set_readme_addon(
                        "Job",
                        job.name,
                        readme_addon,
                    )
                gitsync.content.push_job(job)

        create_root_readme(gitsync)

        gitsync.commit_and_push(commit_msg)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    main()
