# Copyright 2026 Google LLC
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

from typing import TYPE_CHECKING

from core.action_param_mappers import as_csv, non_empty, required
from core.action_wrapper import ActionContext, ActionResult, ActionRunner
from core.consts import INTEGRATION_NAME, INTEGRATION_PARAM_MAPPERS
from core.manager_providers import build_api_manager
from TIPCommon.base.action import EntityTypesEnum

if TYPE_CHECKING:
    from core.api_manager import GoogleCloudIdentityApiManager


SCRIPT_NAME = "AddEntityToDetectorURLList"
SCRIPT_DISPLAY_NAME = "Add Entity To Detector URL List"


def prepare_runner() -> ActionRunner:
    """Prepare action runner.

    Returns:
        The action runner.

    """
    param_mappers = {
        "Detector Policy ID": [required(), non_empty()],
        "URL": [as_csv()],
        "Domain": [as_csv()],
    }

    return ActionRunner(
        main,
        integration_name=INTEGRATION_NAME,
        action_name=f"{INTEGRATION_NAME} - {SCRIPT_NAME}",
        print_params=True,
        supported_entities=[EntityTypesEnum.URL, EntityTypesEnum.DOMAIN],
        enable_default_error_handling=True,
        error_message_format=f"Error executing action “{SCRIPT_DISPLAY_NAME}”. "
        f"Reason: {{error}}",
        action_param_mappers=param_mappers,
        integration_param_mappers=INTEGRATION_PARAM_MAPPERS,
        injectables={"api_manager": build_api_manager},
    )


def main(
    context: ActionContext,
    result: ActionResult,
    api_manager: GoogleCloudIdentityApiManager,
) -> None:
    """Add entity to detector URL list.

    Args:
        context: The action context.
        result: The action result.
        api_manager: The API manager.

    """
    logger = context.get_logger()
    api_manager.test_connectivity()

    policy_id: str = context.action_parameters.get("Detector Policy ID")
    urls_param: list[str] = context.action_parameters.get("URL", [])
    domains_param: list[str] = context.action_parameters.get("Domain", [])

    all_urls_to_block: list[str] = []
    all_urls_to_block.extend(urls_param)
    all_urls_to_block.extend(domains_param)
    all_urls_to_block.extend(e.identifier for e in context.get_entities())

    if not all_urls_to_block:
        result.value = True
        result.output_message = "No entities, domains or url provided to block"
        return

    logger.info("Successfully identified URLs to block.")

    updated_policy = api_manager.update_url_list_detector_policy(
        policy_id=policy_id, urls=all_urls_to_block
    )
    result.json_result = updated_policy.to_dict()

    result.value = True
    urls_str = ", ".join(all_urls_to_block)
    result.output_message = (
        f"Successfully blocked the following URLs using Cloud Identity: {urls_str}"
    )


if __name__ == "__main__":
    prepare_runner().run()
