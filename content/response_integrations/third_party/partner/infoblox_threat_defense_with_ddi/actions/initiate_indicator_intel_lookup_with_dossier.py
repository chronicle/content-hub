from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param
from ..core.datamodels import DossierWaitResult, DossierJobResult
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    COMMON_ACTION_ERROR_MESSAGE,
    INITIATE_INDICATOR_INTEL_LOOKUP_WITH_DOSSIER_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
)
from ..core.utils import (
    validate_required_string,
    get_integration_params,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = INITIATE_INDICATOR_INTEL_LOOKUP_WITH_DOSSIER_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    indicator_type = extract_action_param(
        siemplify,
        param_name="Indicator Type",
        input_type=str,
        is_mandatory=True,
        print_value=True,
        default_value="Host",
    )
    indicator_value = extract_action_param(
        siemplify,
        param_name="Indicator Value",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    source = extract_action_param(
        siemplify,
        param_name="Source",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    wait_for_results = extract_action_param(
        siemplify,
        param_name="Wait for Results",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=False,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        # --- Validations ---
        indicator_value = validate_required_string(indicator_value, "Indicator Value")
        if source:
            source = source.strip()

        # --- API Manager ---
        api_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = api_manager.initiate_indicator_intel_lookup_with_dossier(
            indicator_type=indicator_type,
            indicator_value=indicator_value,
            source=source,
            wait_for_results=wait_for_results,
        )

        # --- Output Formatting ---
        results = response.get("results")
        table_results = []
        if wait_for_results:
            # Table: Source, Status, Data, Time, Version
            if results and isinstance(results, list):
                for item in results[:MAX_TABLE_RECORDS]:
                    model = DossierWaitResult(item)
                    table_results.append(model.to_csv())
            output_message = (
                f"Successfully retrieved {len(results)} dossier results for indicator. "
                f"Showing up to {MAX_TABLE_RECORDS} in table."
            )
        else:
            # Table: Job ID, Status
            job_id = response.get("job_id")
            status_val = response.get("status")
            model = DossierJobResult({"job_id": job_id, "status": status_val})
            table_results.append(model.to_csv())
            output_message = "Dossier lookup initiated. Job ID and status returned."

        siemplify.result.add_result_json(json.dumps(response))
        if table_results:
            siemplify.result.add_data_table(
                title="Dossier Lookup Results", data_table=construct_csv(table_results)
            )
        else:
            output_message = "No dossier data found."

    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            INITIATE_INDICATOR_INTEL_LOOKUP_WITH_DOSSIER_SCRIPT_NAME, e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
