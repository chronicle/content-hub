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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager


ATP_PROVIDER = "SymantecATP"
ACTION_NAME = "SymantecATP_Revoke From Blacklist"
INSIGHT_MESSAGE = "{0} revoked from blacklist."


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(ATP_PROVIDER)
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    atp_manager = SymantecATPManager(
        conf.get("API Root"),
        conf.get("Client ID"),
        conf.get("Client Secret"),
        verify_ssl,
    )

    errors = []
    revoked_entities = []
    result_value = False

    for entity in siemplify.target_entities:
        try:

            result = atp_manager.delete_blacklist_policy_by_identifier(
                entity.identifier
            )

            if result:
                revoked_entities.append(entity)
                siemplify.add_entity_insight(
                    entity,
                    INSIGHT_MESSAGE.format(entity.identifier),
                    triggered_by=ATP_PROVIDER,
                )
                result_value = True

        except Exception as err:
            error_message = (
                f'Error revoke "{entity.identifier}" from blacklist, Error: {err}'
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    if result_value:
        output_message = f"{','.join([entity.identifier for entity in revoked_entities])} were revoked from blacklisted."
    else:
        output_message = "No entities were revoked from blacklisted."

    # Attach errors if exists.
    if errors:
        output_message = "{0},\n\nERRORS:\n{1} ".format(
            output_message, "\n".join(errors)
        )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
