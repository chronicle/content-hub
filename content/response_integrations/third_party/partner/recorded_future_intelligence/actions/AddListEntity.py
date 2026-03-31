############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

import json

from psengine.config import Config
from psengine.entity_lists import EntityListMgr, ListApiError
from pydantic import ValidationError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import PROVIDER_NAME
from ..core.UtilsManager import map_secops_entities_to_rf
from ..core.version import __version__ as version


@output_handler
def main():
    siemplify = SiemplifyAction()

    api_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="ApiKey",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    list_id = extract_action_param(
        siemplify,
        param_name="List ID",
        is_mandatory=True,
        print_value=True,
    )
    entity_id = extract_action_param(
        siemplify,
        param_name="Entity ID",
        is_mandatory=False,
        print_value=True,
    )
    entity_name = extract_action_param(
        siemplify,
        param_name="Entity Name",
        is_mandatory=False,
        print_value=True,
    )
    entity_type = extract_action_param(
        siemplify,
        param_name="Entity Type",
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    is_success = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    if entity_id:
        entities = [entity_id]
        siemplify.LOGGER.info(f"Entity ID parameter supplied, target entity: {entities}")
    elif bool(entity_name) and bool(entity_type):
        entities = [(entity_name, entity_type)]
        siemplify.LOGGER.info(
            f"Entity Name and Type parameters supplied, target entity: {entities}"
        )
    else:
        entities = map_secops_entities_to_rf(siemplify.target_entities)
        siemplify.LOGGER.info(
            f"No Entity parameters supplied, defaulting to Case Target Entities: {entities}"
        )

    try:
        siemplify.LOGGER.info("Initializing psengine configuration")
        Config.init(
            client_verify_ssl=verify_ssl,
            rf_token=api_key,
            app_id=f"ps-google-soar/{version}",
        )
        siemplify.LOGGER.info("Initializing psengine EntityListMgr")
        list_mgr = EntityListMgr()
        siemplify.LOGGER.info(f"Fetching List from Recorded Future: {list_id}")
        fetch_resp = list_mgr.fetch(list_=list_id)

        siemplify.LOGGER.info(f"Adding {len(entities)} entities from SecOps case to list")
        add_resp = fetch_resp.bulk_add(entities=entities)

        siemplify.result.add_result_json(json.dumps(add_resp))

        if added := add_resp.get("added", []):
            output_message += f"Successfully added {len(added)} entities to list."
        if error := add_resp.get("error", []):
            output_message += f"\nError adding {len(error)} entities to list."
        if unchanged := add_resp.get("unchanged", []):
            output_message += f"\n{len(unchanged)} entities unchanged."

    except ValidationError as err:
        output_message = f"Error with List Manager parameters: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValueError as err:
        output_message = f"Error creating List Manager: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ListApiError as err:
        output_message = f"Error calling Recorded Future List API: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED

    except Exception as err:
        output_message = f"Error executing Fetch List action: {err}"
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
