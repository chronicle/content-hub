from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ZendeskManager import ZendeskManager
import json

NO_RESULTS = 0


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Zendesk")
    user_email = conf["User Email Address"]
    api_token = conf["Api Token"]
    server_address = conf["Server Address"]
    zendesk = ZendeskManager(user_email, api_token, server_address)

    query = siemplify.parameters["Search Query"]
    search_result = zendesk.search_tickets(query)

    if search_result["count"] != NO_RESULTS:
        results = search_result["results"]
        for result in results:
            result_json = json.dumps(result, indent=4, sort_keys=True)
            siemplify.result.add_json(f"Ticket - {result['id']}", result_json)

        output_message = f"Successfully found {search_result['count']} results for {query} search query."
        result_value = search_result["count"]
    else:
        output_message = f"Can not find results for {query} search query."
        result_value = NO_RESULTS

    siemplify.result.add_result_json(search_result)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
