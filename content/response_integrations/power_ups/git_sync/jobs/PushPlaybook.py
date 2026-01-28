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

    if not playbooks_allowlist and not folders_allowlist:
        raise Exception("Playbook or Folder allowlist not provided")

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)
        installed_playbooks = gitsync.api.get_playbooks(chronicle_soar=siemplify)

        for playbook in installed_playbooks:
            if (
                playbook.get("name") in playbooks_allowlist
                or playbook.get("categoryName") in folders_allowlist
            ):
                siemplify.LOGGER.info(f"Pushing Playbook {playbook['name']}")

                if readme_addon:
                    siemplify.LOGGER.info(
                        "Readme addon found - adding to GitSync metadata file (GitSync.json)",
                    )
                    gitsync.content.metadata.set_readme_addon(
                        "Playbook",
                        playbook.get("name"),
                        readme_addon,
                    )

                playbook = gitsync.api.get_playbook(
                    chronicle_soar=siemplify,
                    identifier=playbook.get("identifier"),
                )
                workflow = Workflow(playbook)
                workflow.update_instance_name_in_steps(gitsync.api, siemplify)
                gitsync.content.push_playbook(workflow)

                if include_blocks:
                    for block in workflow.get_involved_blocks():
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
                        block = Workflow(
                            gitsync.api.get_playbook(
                                chronicle_soar=siemplify,
                                identifier=installed_block.get("identifier"),
                            ),
                        )
                        block.update_instance_name_in_steps(gitsync.api, siemplify)
                        gitsync.content.push_playbook(block)
            else:
                siemplify.LOGGER.warn(
                    f"Playbook {playbook.get('name')} not found, Skipping",
                )

        gitsync.update_readme(create_root_readme(gitsync), "Playbooks")
        gitsync.commit_and_push(commit_msg)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
