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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import add_comment_to_entity

# Example Consts:
INTEGRATION_NAME = "Tools"

SCRIPT_NAME = "Add Comment To Entity Log"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    comment = siemplify.extract_action_param(
        param_name="Comment",
        is_mandatory=True,
        print_value=True,
    )
    user = siemplify.extract_action_param(
        param_name="User",
        is_mandatory=True,
        print_value=True,
    )
    result_value = None
    output_message = ""

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        for entity in siemplify.target_entities:
            siemplify.LOGGER.info(f"Adding comment to entity: {entity.identifier}")

            add_comment_to_entity(
                chronicle_soar=siemplify,
                content=comment,
                author=user,
                entity_type=entity.entity_type,
                entity_identifier=entity.identifier,
                entity_environment=siemplify._environment,
            )

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")
            output_message += (
                f"{user} Added comment to entity: {entity.identifier}, "
                f"Environment: {siemplify._environment}. Comment: {comment}\n"
            )

    except Exception as e:
        siemplify.LOGGER.exception("General error performing action %s", SCRIPT_NAME)
        siemplify.LOGGER.exception(e)
        raise

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
