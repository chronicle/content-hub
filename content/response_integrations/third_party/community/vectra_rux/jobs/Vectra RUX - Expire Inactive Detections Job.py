from __future__ import annotations

from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import unix_now

from ..core.constants import (
    CASES_TIMESTAMP_DB_KEY,
    DEFAULT_HOURS_BACKWARDS,
    EXPIRE_INACTIVE_DETECTIONS_JOB_SCRIPT_NAME,
    INACTIVE_DETECTION_STATE,
    MAX_OPEN_CASES,
    UNIX_FORMAT,
)
from ..core.UtilsManager import (
    expire_inactive_detections,
    get_last_success_time_for_job,
    save_timestamp_for_job,
    validate_integer,
    validate_limit_param,
)
from ..core.VectraRUXExceptions import InvalidIntegerException, VectraRUXException
from ..core.VectraRUXManager import VectraRUXManager


def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = EXPIRE_INACTIVE_DETECTIONS_JOB_SCRIPT_NAME

    # INIT Job PARAMETERS:
    api_root = siemplify.extract_job_param(
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    ).strip()

    client_id = siemplify.extract_job_param(
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    ).strip()

    client_secret = siemplify.extract_job_param(
        param_name="Client Secret",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    ).strip()

    hours_backwards = siemplify.extract_job_param(
        param_name="Max Hours Backwards",
        input_type=str,
        print_value=True,
        default_value=DEFAULT_HOURS_BACKWARDS,
    ).strip() or DEFAULT_HOURS_BACKWARDS

    environments = siemplify.extract_job_param(
        param_name="Environments",
        is_mandatory=True,
        print_value=True,
        default_value="Default Environment",
    )

    product_names = siemplify.extract_job_param(
        param_name="Products",
        is_mandatory=True,
        print_value=True,
        default_value="Vectra RUX",
    )

    max_detections_to_fetch = siemplify.extract_job_param(
        param_name="Max Detections To Fetch",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    max_cases_to_process = siemplify.extract_job_param(
        param_name="Max Cases To Process",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        default_value="2000",
    ).strip() or "2000"

    try:
        hours_backwards = validate_integer(
            hours_backwards,
            field_name="Max Hours Backwards",
            zero_allowed=True,
            allow_negative=False,
        )
        if hours_backwards == 0:
            raise VectraRUXException("'Max Hours Backwards' must be greater than 0.")

        environments = [env.strip() for env in environments.split(",") if env.strip()]
        product_names = [
            product.strip() for product in product_names.split(",") if product.strip()
        ]
        max_detections_to_fetch = validate_integer(
            validate_limit_param(max_detections_to_fetch, param_name="Max Detections To Fetch"),
            zero_allowed=True,
            field_name="Max Detections To Fetch",
        )
        max_cases_to_process = validate_integer(
            max_cases_to_process,
            field_name="Max Cases To Process",
            allow_negative=False,
        )
        if max_cases_to_process > MAX_OPEN_CASES:
            raise VectraRUXException(
                f"'Max Cases To Process' must not exceed {MAX_OPEN_CASES}, got {max_cases_to_process}.",
            )

        # Check if required fields are provided or not
        if not (environments and product_names):
            raise VectraRUXException(
                "The required parameter values cannot be empty. Please provide values for the following required parameters: ['Environments', 'Products'].",
            )

        cases_last_success_timestamp = get_last_success_time_for_job(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
            timestamp_key=CASES_TIMESTAMP_DB_KEY,
        )

        vectra_manager = VectraRUXManager(
            api_root,
            client_id=client_id,
            client_secret=client_secret,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info("Fetching inactive detections from Vectra...")
        inactive_detections = vectra_manager.list_detections(
            limit=max_detections_to_fetch,
            state=INACTIVE_DETECTION_STATE,
        )
        inactive_detection_ids = {
            str(detection.get("id"))
            for detection in inactive_detections
            if detection.get("id") is not None
        }
        siemplify.LOGGER.info(
            f"Found {len(inactive_detection_ids)} inactive detections on Vectra.",
        )

        cases_checkpoint = None
        if inactive_detection_ids:
            cases_checkpoint = expire_inactive_detections(
                siemplify,
                inactive_detection_ids,
                cases_last_success_timestamp,
                False,
                environments=environments,
                product_names=product_names,
                max_cases=max_cases_to_process,
            )

        new_checkpoint = cases_checkpoint + 1 if cases_checkpoint else unix_now()
        siemplify.LOGGER.info(f"Saving checkpoint - {new_checkpoint}.")
        save_timestamp_for_job(
            siemplify,
            new_timestamp=new_checkpoint,
            timestamp_key=CASES_TIMESTAMP_DB_KEY,
        )

    except InvalidIntegerException as e:
        siemplify.LOGGER.error("Error while checking hours_backwards/limit")
        siemplify.LOGGER.exception(e)
        raise
    except VectraRUXException as e:
        siemplify.LOGGER.error(
            f"Exception occured while performing Vectra RUX Job {EXPIRE_INACTIVE_DETECTIONS_JOB_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
        raise
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing Job {EXPIRE_INACTIVE_DETECTIONS_JOB_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
