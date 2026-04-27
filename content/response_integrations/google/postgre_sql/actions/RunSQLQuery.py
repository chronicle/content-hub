from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from ..core.PostgreSQLManager import PostgreSQLManager, PostgreSQLException
import json
import datetime

PROVIDER_NAME = "PostgreSQL"
SCRIPT_NAME = f"{PROVIDER_NAME} - Run SQL Query"


def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration(PROVIDER_NAME)

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    server_addr = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]
    port = conf.get("Port")

    database = siemplify.parameters["Database Name"]
    query = siemplify.parameters["Query"]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        postgres_manager = PostgreSQLManager(
            username=username,
            password=password,
            server=server_addr,
            database=database,
            port=port,
        )

        # Run search query
        results = postgres_manager.execute(query) or []
        # Close the connection
        postgres_manager.close()

        if results:
            # Construct csv
            csv_output = postgres_manager.construct_csv(results)
            siemplify.result.add_data_table("PostgreSQL Query Results", csv_output)

        siemplify.result.add_result_json(json.dumps(results, default=datetime_handler))
        siemplify.end(
            f"Successfully finished search. Found {len(results)} rows.",
            json.dumps(results, default=datetime_handler),
        )
    except (PostgreSQLException, Exception) as e:
        e = str(e)
        output_message = f"Failed to execute query. Error: {e}"
        result = "false"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        siemplify.end(output_message, result, status)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")


if __name__ == "__main__":
    main()
