# Copyright 2026 RansomLeak
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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.constants import DEFAULT_MAX_RESULTS, LIST_LEARNING_PATHS_SCRIPT_NAME
from ..core.exceptions import RansomLeakValidationError
from ..core.utils import build_manager

ACTION_NAME = "List Learning Paths"


@output_handler
def main() -> None:
    """List published RansomLeak learning paths, optionally filtered by name."""
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_LEARNING_PATHS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    name_filter = extract_action_param(siemplify, param_name="Filter Value", print_value=True) or ""
    max_results = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        default_value=DEFAULT_MAX_RESULTS,
        input_type=int,
        print_value=True,
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    try:
        if max_results is None or max_results < 1:
            msg = "'Max Results To Return' must be a positive number."
            raise RansomLeakValidationError(msg)
        manager = build_manager(siemplify)
        needle = name_filter.strip().lower()
        paths = [
            {"id": p.get("id"), "name": p.get("name"), "description": p.get("description")}
            for p in manager.list_learning_paths()
            if not needle or needle in (p.get("name") or "").lower()
        ][:max_results]

        if paths:
            siemplify.result.add_result_json(paths)
            siemplify.result.add_data_table(
                "RansomLeak Learning Paths",
                construct_csv([
                    {"ID": p["id"], "Name": p["name"], "Description": p["description"] or ""} for p in paths
                ]),
            )
            output_message = f"Successfully found {len(paths)} learning path(s) in RansomLeak."
            result_value = True
        else:
            output_message = "No learning paths were found in RansomLeak for the provided criteria."
    except Exception as error:
        siemplify.LOGGER.exception(f'Error executing action "{ACTION_NAME}". Reason: {error}')
        output_message = f'Error executing action "{ACTION_NAME}". Reason: {error}'
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
