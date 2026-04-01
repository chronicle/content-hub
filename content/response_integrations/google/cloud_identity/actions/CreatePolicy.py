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

from core.action_param_mappers import (
    as_dataclass_from_dict,
    as_dict_from_yaml,
    non_empty,
    required,
)
from core.action_wrapper import ActionContext, ActionResult, ActionRunner
from core.consts import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME, INTEGRATION_PARAM_MAPPERS
from core.datamodels import Policy
from core.manager_providers import build_api_manager

if TYPE_CHECKING:
    from core.api_manager import GoogleCloudIdentityApiManager


SCRIPT_NAME = "CreatePolicy"
SCRIPT_DISPLAY_NAME = "Create Policy"


def prepare_runner() -> ActionRunner:
    """Prepare action runner.

    Returns:
        The action runner.

    """
    param_mappers = {
        "Policy Entry": [
            required(),
            non_empty(),
            as_dict_from_yaml(),
            as_dataclass_from_dict(Policy),
        ],
    }

    return ActionRunner(
        main,
        integration_name=INTEGRATION_NAME,
        action_name=f"{INTEGRATION_NAME} - {SCRIPT_NAME}",
        print_params=True,
        supported_entities=[],
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
    """Create a new policy.

    Args:
        context: The action context.
        result: The action result.
        api_manager: The API manager.

    """
    logger = context.get_logger()
    api_manager.test_connectivity()
    logger.info("Getting policy entry parameters...")
    policy_entry: Policy = context.action_parameters.get("Policy Entry")
    logger.info("Creating policy entry...")
    created_policy = api_manager.create_policy(policy_entry)
    logger.info("Policy entry created successfully...")
    result.value = True
    result.json_result = created_policy.to_dict()
    result.output_message = (
        f"Successfully added a new policy in {INTEGRATION_DISPLAY_NAME}."
    )


if __name__ == "__main__":
    prepare_runner().run()
