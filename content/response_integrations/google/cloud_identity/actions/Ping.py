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

from core.action_wrapper import ActionContext, ActionResult, ActionRunner
from core.consts import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME, INTEGRATION_PARAM_MAPPERS
from core.manager_providers import build_api_manager

if TYPE_CHECKING:
    from core.api_manager import GoogleCloudIdentityApiManager


SCRIPT_NAME = "Ping"


def prepare_runner() -> ActionRunner:
    """Prepare action runner.

    Returns:
        The action runner.

    """
    return ActionRunner(
        main,
        integration_name=INTEGRATION_NAME,
        action_name=f"{INTEGRATION_NAME} - {SCRIPT_NAME}",
        print_params=True,
        enable_default_error_handling=True,
        error_message_format=f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} "
        f"server. Error is: {{error}}",
        integration_param_mappers=INTEGRATION_PARAM_MAPPERS,
        injectables={"api_manager": build_api_manager},
    )


def main(
    _: ActionContext, result: ActionResult, api_manager: GoogleCloudIdentityApiManager
) -> None:
    """Ping action.

    Args:
        _: The action context.
        result: The action result.
        api_manager: The API manager.

    """
    api_manager.test_connectivity()
    result.output_message = (
        f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} "
        f"server with the provided connection parameters!"
    )


if __name__ == "__main__":
    prepare_runner().run()
