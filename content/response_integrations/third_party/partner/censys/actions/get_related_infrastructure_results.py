from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.censys_exceptions import CensysException
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    GET_RELATED_INFRA_RESULTS_SCRIPT_NAME,
    JOB_ID_REQUIRED_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    TARGET_TYPE_CERTIFICATE,
    TARGET_TYPE_HOST,
    TARGET_TYPE_WEB_PROPERTY,
)
from ..core.datamodels import RelatedInfraResultModel
from ..core.utils import get_integration_params


@output_handler
def main():
    """Get the detailed results from a completed CensEye job.

    This action retrieves the pivot results from a completed CensEye job, formats them
    into a table with 5 columns, and generates Censys search URLs for each pivot.
    Maximum 50 results per job.

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Summary of results retrieved
            - result_value (bool): True if successful, False otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        ValueError: If Job ID validation fails
        CensysException: If API call fails
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RELATED_INFRA_RESULTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

    job_id = siemplify.extract_action_param(
        param_name="Job ID", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        if not job_id or not job_id.strip():
            raise ValueError(JOB_ID_REQUIRED_ERROR)

        job_id = job_id.strip()

        censys_manager = APIManager(
            api_key,
            organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Retrieving results for CensEye job: {job_id}")
        response = censys_manager.get_censeye_job_results(job_id)

        siemplify.result.add_result_json(response)

        result = response.get("result", {})
        results = result.get("results", [])

        target_info = result.get("target", {})
        if "host_id" in target_info:
            target_type = TARGET_TYPE_HOST
        elif "webproperty_id" in target_info:
            target_type = TARGET_TYPE_WEB_PROPERTY
        elif "certificate_id" in target_info:
            target_type = TARGET_TYPE_CERTIFICATE
        else:
            target_type = TARGET_TYPE_HOST

        if results:
            result_models = []
            total_assets = 0

            for index, result_data in enumerate(results, start=1):
                model = RelatedInfraResultModel(
                    raw_data=result_data,
                    index=index,
                )
                result_models.append(model)
                total_assets += model.count

            csv_data = [model.to_csv() for model in result_models]
            if csv_data:
                siemplify.result.add_data_table(
                    "Related Infrastructure Pivots", construct_csv(csv_data), "Censys"
                )

            output_message = (
                f"Successfully retrieved {len(results)} related infrastructure pivot(s) "
                f"for job {job_id}. Total assets across all pivots: {total_assets}"
            )
            siemplify.LOGGER.info(output_message)

        else:
            output_message = (
                f"No related infrastructure results found for job {job_id}."
            )
            siemplify.LOGGER.info(output_message)

    except ValueError as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_RELATED_INFRA_RESULTS_SCRIPT_NAME, str(e)
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
