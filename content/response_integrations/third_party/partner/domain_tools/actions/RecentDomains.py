"""
Action script for Domain Tools - Recent Domains.

DEPRECATED - Search for new domains containing a  particular word
The phisheye product has been Deprecated by DomainTools
"""

from __future__ import annotations

# Imports
from soar_sdk.SiemplifyAction import *  # type: ignore[import-not-found]
from soar_sdk.SiemplifyUtils import *  # type: ignore[import-not-found]
from soar_sdk.SiemplifyUtils import output_handler  # type: ignore[import-not-found]

from ..core.DomainToolsManager import DomainToolsManager


@output_handler
def main():
    # Configurations
    siemplify = SiemplifyAction()
    configuration_settings = siemplify.get_configuration("DomainTools")
    username = configuration_settings["Username"]
    api_key = configuration_settings["ApiToken"]
    verify_ssl = configuration_settings["Verify SSL"]
    domaintools_manager = DomainToolsManager(username, api_key, verify_ssl=verify_ssl)

    # Parameters
    string_query = siemplify.parameters["String Query"]

    # Variables Definition.
    output_message = ""
    entities_to_update = []
    result_value = False

    res = domaintools_manager.get_recent_domains_by_string_query(string_query)

    if res:
        # Push entity to entities to update array.
        entities_to_update.append(entity)
        # Convert response dict to flat dict.
        flat_dict_res = dict_to_flat(res)
        # Convert response to CSV format string list.
        csv_res = flat_dict_to_csv(flat_dict_res)
        # Print result table.
        siemplify.result.add_data_table(f"Result For: {string_query}", csv_res)
        # Return true on action result.
        result_value = True
    else:
        pass

    # Organize output message.
    if entities_to_update:
        output_message = f"Found results for: {string_query}"
    else:
        output_message = "No results found."

    # End action
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
