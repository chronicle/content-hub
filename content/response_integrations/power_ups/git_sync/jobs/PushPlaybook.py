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

from jinja2 import Template
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import PLAYBOOKS_ROOT_README
from ..core.definitions import Workflow
from ..core.GitSyncManager import GitSyncManager

SCRIPT_NAME = "Push Playbook"


def create_root_readme(gitsync: GitSyncManager):
    playbooks = [pb.raw_data for pb in gitsync.content.get_playbooks()]
    readme = Template(PLAYBOOKS_ROOT_README)
    return readme.render(playbooks=playbooks)


def extract_list_parameter(siemplify: SiemplifyJob, param_name: str):
    return [
        _f
        for _f in [
            x.strip() for x in siemplify.extract_job_param(param_name, " ").split(",")
        ]
        if _f
    ]


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME
    playbooks_allowlist = extract_list_parameter(siemplify, "Playbook Whitelist")
    folders_allowlist = extract_list_parameter(siemplify, "Folders Whitelist")
    commit_msg = siemplify.extract_job_param("Commit")
    readme_addon = siemplify.extract_job_param("Readme Addon", input_type=str)
    include_blocks = siemplify.extract_job_param(
        "Include Playbook Blocks",
        input_type=bool,
    )

    siemplify.LOGGER.info(f"[JOB_LOG] Starting Push Playbook with Whitelists: Playbook Whitelist={playbooks_allowlist}, Folders Whitelist={folders_allowlist}")
    siemplify.LOGGER.info(f"[JOB_LOG] Push Options: Commit={commit_msg}, Readme Addon={'Yes' if readme_addon else 'No'}, Include Playbook Blocks={include_blocks}")

    if not playbooks_allowlist and not folders_allowlist:
        raise Exception("Playbook or Folder allowlist not provided")

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)
        installed_playbooks = gitsync.api.get_playbooks()
        siemplify.LOGGER.info(f"[JOB_LOG] Retrieved {len(installed_playbooks)} installed playbooks/blocks from SOAR")

        for playbook in installed_playbooks:
            name = playbook.get("name")
            category = playbook.get("categoryName")
            matched = (
                name in playbooks_allowlist
                or category in folders_allowlist
            )
            siemplify.LOGGER.info(f"  Checking playbook '{name}' (category '{category}'): Matched={matched}")
            if matched:
                siemplify.LOGGER.info(f"Pushing Playbook {name}")

                if readme_addon:
                    siemplify.LOGGER.info(
                        "Readme addon found - adding to GitSync metadata file (GitSync.json)",
                    )
                    gitsync.content.metadata.set_readme_addon(
                        "Playbook",
                        name,
                        readme_addon,
                    )

                siemplify.LOGGER.info(f"[JOB_LOG] Fetching full playbook data for '{name}' (id='{playbook.get('identifier')}')")
                playbook_details = gitsync.api.get_playbook(playbook.get("identifier"))
                workflow = Workflow(playbook_details)
                workflow.update_instance_name_in_steps(gitsync.api, siemplify)
                gitsync.content.push_playbook(workflow)
                siemplify.LOGGER.info(f"[JOB_LOG] Successfully pushed '{name}' to local content")

                if include_blocks:
                    involved_blocks = workflow.get_involved_blocks()
                    siemplify.LOGGER.info(f"[JOB_LOG] Involved blocks for '{name}': {[b.get('name') for b in involved_blocks]}")
                    for block in involved_blocks:
                        installed_block = next(
                            (
                                x
                                for x in installed_playbooks
                                if x.get("name") == block.get("name")
                            ),
                            None,
                        )
                        if not installed_block:
                            siemplify.LOGGER.warn(
                                f"Block {block.get('name')} wasn't found in the repo, ignoring",
                            )
                            continue
                        siemplify.LOGGER.info(f"[JOB_LOG] Fetching full block data for '{block.get('name')}' (id='{installed_block.get('identifier')}')")
                        block_details = Workflow(
                            gitsync.api.get_playbook(installed_block.get("identifier")),
                        )
                        block_details.update_instance_name_in_steps(gitsync.api, siemplify)
                        gitsync.content.push_playbook(block_details)
                        siemplify.LOGGER.info(f"[JOB_LOG] Successfully pushed involved block '{block.get('name')}' to local content")
            else:
                siemplify.LOGGER.warn(
                    f"Playbook {name} not found, Skipping",
                )

        gitsync.update_readme(create_root_readme(gitsync), "Playbooks")
        siemplify.LOGGER.info(f"[JOB_LOG] Commit and Push changes with message: '{commit_msg}'")
        gitsync.commit_and_push(commit_msg)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
