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
from psengine.detection import DetectionMgr, DetectionRuleSearchError
from pydantic import ValidationError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.validation import ParameterValidator

from ..core.constants import CSV_DELIMETER, DETECTION_RULE_TYPES, PROVIDER_NAME
from ..core.UtilsManager import map_secops_entities_to_rf
from ..core.version import __version__ as version


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
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
    detection_rule = param_validator.validate_csv(
        param_name="detection_rule",
        csv_string=extract_action_param(
            siemplify,
            param_name="Detection Rule Type",
            input_type=str,
            print_value=True,
            default_value=None,
            is_mandatory=False,
        ),
        delimiter=CSV_DELIMETER,
        possible_values=DETECTION_RULE_TYPES,
        default_value=None,
    )
    entities = extract_action_param(
        siemplify,
        param_name="Filter on Target Entities",
        input_type=bool,
        print_value=True,
        default_value=False,
        is_mandatory=False,
    )
    entity_ids = param_validator.validate_csv(
        param_name="entity_ids",
        csv_string=extract_action_param(
            siemplify,
            param_name="Entity ID",
            input_type=str,
            print_value=True,
            default_value=None,
            is_mandatory=False,
        ),
        delimiter=CSV_DELIMETER,
        default_value=None,
    )
    created_before = extract_action_param(
        siemplify,
        param_name="Created Before",
        input_type=str,
        print_value=True,
        default_value=None,
        is_mandatory=False,
    )
    created_after = extract_action_param(
        siemplify,
        param_name="Created After",
        input_type=str,
        print_value=True,
        default_value=None,
        is_mandatory=False,
    )
    updated_before = extract_action_param(
        siemplify,
        param_name="Updated Before",
        input_type=str,
        print_value=True,
        default_value=None,
        is_mandatory=False,
    )
    updated_after = extract_action_param(
        siemplify,
        param_name="Updated After",
        input_type=str,
        print_value=True,
        default_value=None,
        is_mandatory=False,
    )
    doc_id = extract_action_param(
        siemplify,
        param_name="Detection Rule ID",
        input_type=str,
        print_value=True,
        default_value=None,
        is_mandatory=False,
    )
    title = extract_action_param(
        siemplify,
        param_name="Detection Rule Title",
        input_type=str,
        print_value=True,
        default_value=None,
        is_mandatory=False,
    )
    tagged_entities = extract_action_param(
        siemplify,
        param_name="Tagged Entities",
        input_type=bool,
        print_value=True,
        default_value=None,
        is_mandatory=False,
    )
    max_results = extract_action_param(
        siemplify,
        param_name="Max Results",
        input_type=int,
        print_value=True,
        default_value=10,
        is_mandatory=False,
    )

    is_success = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    try:
        target_entities = (
            map_secops_entities_to_rf(siemplify.target_entities) if entities else entity_ids
        )
        if target_entities:
            siemplify.LOGGER.info(
                f"Searching detection rules for target entities: {target_entities}"
            )
        siemplify.LOGGER.info("Initializing psengine configuration")
        Config.init(
            client_verify_ssl=verify_ssl,
            rf_token=api_key,
            app_id=f"ps-google-soar/{version}",
        )
        siemplify.LOGGER.info("Initializing psengine DetectionMgr")
        detection_mgr = DetectionMgr()
        siemplify.LOGGER.info("Searching Detection Rules in Recorded Future")
        search_detection_resp = detection_mgr.search(
            detection_rule=detection_rule,
            entities=target_entities,
            created_before=created_before,
            created_after=created_after,
            updated_before=updated_before,
            updated_after=updated_after,
            doc_id=doc_id,
            title=title,
            tagged_entities=tagged_entities,
            max_results=max_results,
        )
        data = [rule.json() for rule in search_detection_resp]
        siemplify.result.add_result_json(data)
        output_message = (
            f"Successfully ran Search Detection Rules action. Found {len(data)} rule(s)."
        )

    except ValidationError as err:
        output_message = f"Invalid parameters for Search Detection Rules action {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValueError as err:
        output_message = f"Error creating Detection Rule Manager {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except DetectionRuleSearchError as err:
        output_message = f"Error calling Detection Rule API {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except Exception as e:
        output_message = "General error performing Search Detection Rules action"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("\n----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {is_success}")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
