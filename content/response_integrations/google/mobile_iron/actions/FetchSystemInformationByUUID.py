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

# Imports
from ..core.MobileIronManager import MobileIronManager
from soar_sdk.SiemplifyAction import SiemplifyAction

# Consts.
PROVIDER_NAME = "MobileIron"
ACTION_NAME = "MobileIron_Fetch System Information by UUID"
TABLE_HEADER = "Devices"


@output_handler
def main():
    # Variables Definition.
    result_value = False

    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    configuretion_settings = siemplify.get_configuration(PROVIDER_NAME)
    api_root = configuretion_settings["API Root"]
    username = configuretion_settings["Username"]
    password = configuretion_settings["Password"]
    admin_device_id = configuretion_settings.get("Admin Device ID", 1)
    connected_cloud = (
        configuretion_settings.get("Cloud Instance", "false").lower() == "true"
    )
    verify_ssl = configuretion_settings.get("Verify SSL", "false").lower() == "true"

    mobile_iron_manager = MobileIronManager(
        api_root, username, password, admin_device_id, connected_cloud, verify_ssl
    )

    # Parameters.
    device_uuid = siemplify.parameters.get("Device UUID")

    system_information = mobile_iron_manager.get_device_details_by_uuid(device_uuid)

    if system_information:
        siemplify.result.add_entity_table(
            device_uuid,
            mobile_iron_manager.rearrange_details_output(system_information),
        )
        result_value = True
        output_message = f"Found system information for ID '{device_uuid}'"
    else:
        output_message = f"No information was fetched for UUID '{device_uuid}'."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
