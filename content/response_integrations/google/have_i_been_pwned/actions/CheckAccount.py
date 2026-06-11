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
from ..core.HaveIBeenPwnedManager import HaveIBeenPwnedManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import construct_csv, convert_dict_to_json_result_dict

SCRIPT_NAME = "HaveIBeenPwned - CheckAccount"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("HaveIBeenPwned")
    api_key = conf.get("Api Key")
    verify_ssl = str(conf.get("Verify SSL", "False")).lower() == "true"
    hibp_manager = HaveIBeenPwnedManager(api_key, use_ssl=verify_ssl)

    pwned_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.USER:
            if hibp_manager.validate_email(entity.identifier.lower()):
                try:
                    account_breaches_obj = hibp_manager.get_all_breaches_for_an_account(
                        entity.identifier.lower()
                    )
                    account_pastes_obj = hibp_manager.get_all_pastes_for_an_account(
                        entity.identifier
                    )

                    if account_breaches_obj or account_pastes_obj:
                        siemplify.add_entity_insight(
                            entity,
                            "Account have been pwned!",
                            triggered_by="HaveIBeenPwned",
                        )
                        pwned_entities.append(entity.identifier.lower())
                        json_results.update({entity.identifier: {}})

                        if account_pastes_obj:
                            json_results[entity.identifier].update(
                                {
                                    "pastes": [
                                        paste.raw_data for paste in account_pastes_obj
                                    ]
                                }
                            )
                            csv_output = construct_csv(
                                [paste.as_csv() for paste in account_pastes_obj]
                            )
                            siemplify.result.add_data_table(
                                f"{entity.identifier} - Pastes", csv_output
                            )
                        if account_breaches_obj:
                            json_results[entity.identifier].update(
                                {
                                    "breaches": [
                                        breach.raw_data
                                        for breach in account_breaches_obj
                                    ]
                                }
                            )
                            csv_output = construct_csv(
                                [breach.as_csv() for breach in account_breaches_obj]
                            )
                            siemplify.result.add_data_table(
                                f"{entity.identifier} - Breaches", csv_output
                            )

                except Exception as e:
                    # An error occurred - skip entity and continue
                    siemplify.LOGGER.error(
                        f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                    )
                    siemplify.LOGGER.exception(e)

    if pwned_entities:
        output_message = "The following entities were pwned. \n{0}".format(
            ", \n".join(pwned_entities)
        )
        result_value = ", ".join(pwned_entities)
    else:
        output_message = "Good news! No pwnage found."
        result_value = "false"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
