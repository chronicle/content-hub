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

SCRIPT_NAME = "Pull Playbook"


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    pull_allowlist = [
        _f
        for _f in [
            x.strip()
            for x in siemplify.extract_job_param("Playbook Whitelist", " ").split(",")
        ]
        if _f
    ]
    include_blocks = siemplify.extract_job_param(
        "Include Playbook Blocks",
        input_type=bool,
    )

    siemplify.LOGGER.info(f"[JOB_LOG] Starting Pull Playbook with parameters: Playbook Whitelist={pull_allowlist}, Include Playbook Blocks={include_blocks}")

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        playbooks = {}
        for playbook_name in pull_allowlist:
            siemplify.LOGGER.info(f"Pulling {playbook_name}")
            playbook = gitsync.content.get_playbook(playbook_name)
            if not playbook:
                siemplify.LOGGER.info(f"{playbook_name} not found in the repository")
                continue
            siemplify.LOGGER.info(f"[JOB_LOG] Found playbook '{playbook_name}' in repository (identifier='{playbook.identifier}')")
            playbooks[playbook.name] = playbook
            if include_blocks:
                involved_blocks = playbook.get_involved_blocks()
                siemplify.LOGGER.info(f"[JOB_LOG] Involved blocks in repository for '{playbook_name}': {[b.get('name') for b in involved_blocks]}")
                for block in involved_blocks:
                    block_name = block.get("name")
                    if block_name not in playbooks:
                        siemplify.LOGGER.info(f"[JOB_LOG] Fetching block '{block_name}' from repository")
                        block_workflow = gitsync.content.get_playbook(block_name)
                        if block_workflow:
                            siemplify.LOGGER.info(f"[JOB_LOG] Found block '{block_name}' in repository (identifier='{block_workflow.identifier}')")
                            playbooks[block_workflow.name] = block_workflow
                        else:
                            siemplify.LOGGER.warn(f"[JOB_LOG] Block '{block_name}' not found in the repository")

        siemplify.LOGGER.info(f"[JOB_LOG] About to call install_workflows with targets: {list(playbooks.keys())}")
        gitsync.install_workflows(list(playbooks.values()))

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
