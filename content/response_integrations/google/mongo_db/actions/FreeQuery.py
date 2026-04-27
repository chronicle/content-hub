from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.MongoDBManager import MongoDBManager
import json
from TIPCommon import extract_action_param, extract_configuration_param


INTEGRATION_NAME = "MongoDB"


@output_handler
def main():
    siemplify = SiemplifyAction()

    # INIT INTEGRATION CONFIGURATION:
    server = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Server Address"
    )
    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    port = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Port",
        default_value=False,
        input_type=int,
    )
    is_authenticate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use Authentication",
        input_type=bool,
    )

    database = extract_action_param(
        siemplify, param_name="Database Name", is_mandatory=True, print_value=True
    )
    collection = extract_action_param(
        siemplify, param_name="Collection Name", is_mandatory=True, print_value=True
    )
    show_simple_json = extract_action_param(
        siemplify,
        param_name="Return a single JSON result",
        is_mandatory=False,
        default_value=False,
        print_value=True,
    )
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=True, print_value=True
    )

    try:
        query = json.loads(query)

    except Exception as e:
        siemplify.end(f"Invalid json query. Please try again. {e}", "false")

    mongodb_manager = MongoDBManager(
        username=username,
        password=password,
        server=server,
        port=port,
        is_authenticate=is_authenticate,
    )

    # Run search query
    results = (
        mongodb_manager.execute_query(
            query=query, database_name=database, collection_name=collection
        )
        or []
    )

    # Close the connection
    mongodb_manager.close_connection()

    if results and not show_simple_json:
        for i, document in enumerate(results, 1):
            siemplify.result.add_json(
                f"Query Results - Document {i}", json.dumps(document)
            )

        siemplify.end(
            f"Successfully finished search. Found {len(results)} matching documents.",
            "true",
        )

    if results and show_simple_json:
        for i, document in enumerate(results, 1):
            siemplify.result.add_result_json(json.dumps(results))

        siemplify.end(
            f"Successfully finished search. Found {len(results)} matching documents.",
            "true",
        )

    siemplify.result.add_result_json(json.dumps(results or []))

    siemplify.end(f"Cannot find query results. Please check your query {query}", "true")


if __name__ == "__main__":
    main()
