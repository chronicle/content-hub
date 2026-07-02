############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

from psengine.config import Config
from psengine.links import LinksMgr, LinksSearchError
from pydantic import ValidationError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.validation import ParameterValidator

from ..core.constants import CSV_DELIMETER, PROVIDER_NAME
from ..core.UtilsManager import map_secops_entities_to_rf
from ..core.version import __version__ as version


@output_handler
def main():
    siemplify = SiemplifyAction()
    param_validator = ParameterValidator(siemplify=siemplify)

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

    entities = param_validator.validate_csv(
        param_name="entities",
        csv_string=extract_action_param(
            siemplify,
            param_name="Entities",
            input_type=str,
            is_mandatory=False,
            print_value=True,
            remove_whitespaces=True,
        ),
        delimiter=CSV_DELIMETER,
        default_value=None,
    )
    is_target_entities = extract_action_param(
        siemplify,
        param_name="Filter on Target Entities",
        input_type=bool,
        print_value=True,
        default_value=False,
        is_mandatory=False,
    )
    sections = param_validator.validate_csv(
        param_name="sections",
        csv_string=extract_action_param(
            siemplify,
            param_name="Sections",
            input_type=str,
            is_mandatory=False,
            print_value=True,
            remove_whitespaces=True,
        ),
        delimiter=CSV_DELIMETER,
        default_value=None,
    )
    entity_types = param_validator.validate_csv(
        param_name="entity_types",
        csv_string=extract_action_param(
            siemplify,
            param_name="Entity Types",
            input_type=str,
            is_mandatory=False,
            print_value=True,
            remove_whitespaces=True,
        ),
        delimiter=CSV_DELIMETER,
        default_value=None,
    )
    sources = param_validator.validate_csv(
        param_name="sources",
        csv_string=extract_action_param(
            siemplify,
            param_name="Sources",
            input_type=str,
            is_mandatory=False,
            print_value=True,
            remove_whitespaces=True,
        ),
        delimiter=CSV_DELIMETER,
        default_value=None,
    )
    timeframe = extract_action_param(
        siemplify,
        param_name="Timeframe",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    events = param_validator.validate_csv(
        param_name="events",
        csv_string=extract_action_param(
            siemplify,
            param_name="Events",
            input_type=str,
            is_mandatory=False,
            print_value=True,
            remove_whitespaces=True,
        ),
        delimiter=CSV_DELIMETER,
        default_value=None,
    )
    connected_entities = param_validator.validate_csv(
        param_name="connected_entities",
        csv_string=extract_action_param(
            siemplify,
            param_name="Connected Entities",
            input_type=str,
            is_mandatory=False,
            print_value=True,
            remove_whitespaces=True,
        ),
        delimiter=CSV_DELIMETER,
        default_value=None,
    )
    search_scope = extract_action_param(
        siemplify,
        param_name="Search Scope",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
        default_value="medium",
    )
    max_entity_results = extract_action_param(
        siemplify,
        param_name="Max Entity Results",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    is_success = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    try:
        # resolve target entities
        entities = map_secops_entities_to_rf(siemplify.target_entities) if is_target_entities else entities
        
        siemplify.LOGGER.info("Initializing psengine configuration")
        Config.init(
            client_verify_ssl=verify_ssl,
            rf_token=api_key,
            app_id=f"ps-google-soar/{version}",
        )
        siemplify.LOGGER.info("Initializing psengine LinksMgr")
        links_mgr = LinksMgr()
        siemplify.LOGGER.info("Searching links for given target(s)")
        search_resp = links_mgr.search(
            entities=entities,
            sections=sections or None,
            entity_types=entity_types or None,
            sources=sources or None,
            timeframe=timeframe,
            events=events or None,
            connected_entities=connected_entities or None,
            search_scope=search_scope,
            per_entity_type=max_entity_results,
        )
        data = [links_result.json() for links_result in search_resp]
        siemplify.result.add_result_json(data)
        output_message += (
            "Successfully searched links for the given target(s)"
        )

    except ValidationError as err:
        output_message = f"Error with Links Manager parameters: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValueError as err:
        output_message = f"Error creating Links Manager: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except LinksSearchError as err:
        output_message = f"Error searching links data: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED

    except Exception as err:
        output_message = f"Error executing Search Links action: {err}"
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
