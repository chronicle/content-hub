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
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ConnectWiseManager import ConnectWiseManager


@output_handler
def main():

    # Variables Definitions.
    output_message = ""
    result_value = False

    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    # Configuration.
    configuration_settings = siemplify.get_configuration("ConnectWise")
    company_url = configuration_settings["Api Root"]
    company_name = configuration_settings["Company Name"]
    public_key = configuration_settings["Public Key"]
    private_key = configuration_settings["Private Key"]
    client_id = configuration_settings["Client Id"]
    connectwise_manager = ConnectWiseManager(
        company_url, company_name, public_key, private_key, client_id
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    # Parameters.
    ticket_id = siemplify.parameters["Ticket Id"]
    comment = siemplify.parameters["Comment"]
    is_internal = siemplify.parameters.get("Internal", "").lower == "true"

    # Execute Update Ticket.
    result = connectwise_manager.add_comment_to_ticket(
        ticket_id, comment, is_internal
    )  # The result will be a ticket id.

    if result:
        output_message = (
            f"Ticket with id {ticket_id} was updated with comment: {comment}"
        )
        result_value = result
    else:
        output_message = (
            f"There was a problem adding comment to ticket with id: {ticket_id}."
        )
        result_value = False

    siemplify.LOGGER.info(output_message)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\nresult_value: {result_value}"
        f"\noutput_message: {output_message}"
    )
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
