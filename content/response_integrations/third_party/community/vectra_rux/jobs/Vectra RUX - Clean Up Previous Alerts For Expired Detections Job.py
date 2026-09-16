from __future__ import annotations

from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import unix_now

from ..core.constants import (
    CLEAN_UP_PREVIOUS_ALERTS_JOB_SCRIPT_NAME,
    DEFAULT_HOURS_BACKWARDS,
    MAX_OPEN_CASES,
    PREVIOUS_ALERTS_TIMESTAMP_DB_KEY,
    UNIX_FORMAT,
)
from ..core.UtilsManager import (
    close_previous_alerts_for_expired_detections,
    get_last_success_time_for_job,
    save_timestamp_for_job,
    validate_integer,
)
from ..core.VectraRUXExceptions import InvalidIntegerException, VectraRUXException


def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = CLEAN_UP_PREVIOUS_ALERTS_JOB_SCRIPT_NAME

    # INIT Job PARAMETERS:
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

        alerts_last_success_timestamp = get_last_success_time_for_job(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
            timestamp_key=PREVIOUS_ALERTS_TIMESTAMP_DB_KEY,
        )

        alerts_checkpoint, failed_alerts_count = close_previous_alerts_for_expired_detections(
            siemplify,
            alerts_last_success_timestamp,
            False,
            environments=environments,
            product_names=product_names,
            max_cases=max_cases_to_process,
        )

        new_alerts_checkpoint = alerts_checkpoint + 1 if alerts_checkpoint else unix_now()
        siemplify.LOGGER.info(f"Saving checkpoint - {new_alerts_checkpoint}.")
        save_timestamp_for_job(
            siemplify,
            new_timestamp=new_alerts_checkpoint,
            timestamp_key=PREVIOUS_ALERTS_TIMESTAMP_DB_KEY,
        )

        # Checkpoint is saved above regardless, so a retry next run doesn't
        # re-walk cases that were already scanned successfully - only the
        # run's pass/fail status is affected by closures that failed.
        if failed_alerts_count > 0:
            raise VectraRUXException(
                f"Failed to close {failed_alerts_count} alert(s) this run. See job "
                f"logs for details.",
            )

    except InvalidIntegerException as e:
        siemplify.LOGGER.error("Error while checking hours_backwards/max_cases_to_process")
        siemplify.LOGGER.exception(e)
        raise
    except VectraRUXException as e:
        siemplify.LOGGER.error(
            f"Exception occured while performing Vectra RUX Job {CLEAN_UP_PREVIOUS_ALERTS_JOB_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
        raise
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing Job {CLEAN_UP_PREVIOUS_ALERTS_JOB_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
