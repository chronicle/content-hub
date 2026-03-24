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

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
    dict_to_flat,
    flat_dict_to_csv,
    output_handler,
)

from ..core.IPInfoManager import IPInfoManager

ACTION_NAME = "IPInfo Get_IP_Information"
PROVIDER = "IPInfo"
INTEGRATION_PREFIX = "IPInfo"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(PROVIDER)
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    ipinfo_manager = IPInfoManager(conf["API Root"], conf["Token"], verify_ssl)

    success_entities = []
    errors = []
    json_results = {}
    result_value = False

    ip_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == EntityTypes.ADDRESS
    ]

    for entity in ip_entities:
        try:
            ip_information = ipinfo_manager.get_ip_information(entity.identifier)
            if ip_information:
                json_results[entity.identifier] = ip_information
                flat_info = dict_to_flat(ip_information)
                entity.additional_properties.update(
                    add_prefix_to_dict(flat_info, INTEGRATION_PREFIX)
                )
                entity.is_enriched = True
                siemplify.result.add_entity_table(entity.identifier, flat_dict_to_csv(flat_info))
                success_entities.append(entity)
                result_value = True
        except Exception as err:
            error_message = f"Failed fetching information for {entity.identifier}, ERROR: {err}"
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    siemplify.update_entities(success_entities)

    if success_entities:
        output_message = (f"Fetched IP information for: "
                          f"{', '.join([entity.identifier for entity in success_entities])}")
    else:
        output_message = "Mo information fetched for target entities."

    if errors:
        output_message = "{0}\n\nErrors:\n{1}".format(output_message, "\n".join(errors))

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
