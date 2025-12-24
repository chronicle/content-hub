from __future__ import annotations

from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon import extract_action_param

from ..core.constants import (
    CASES_TIMESTAMP_DB_KEY,
    DEFAULT_HOURS_BACKWARDS,
    JOB_SCRIPT_NAME,
    UNIX_FORMAT,
)
from ..core.UtilsManager import (
    clear_empty_cases,
    get_last_success_time_for_job,
    save_timestamp_for_job,
    validate_integer,
)
from ..core.VectraQUXExceptions import InvalidIntegerException, VectraQUXException


def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = JOB_SCRIPT_NAME  # In order to use the SiemplifyLogger

    # INIT ACTION PARAMETERS:
    hours_backwards = extract_action_param(
        siemplify=siemplify,
        param_name="Max Hours Backwards",
        input_type=str,
        print_value=True,
        default_value=DEFAULT_HOURS_BACKWARDS,
    ).strip()

    environments = extract_action_param(
        siemplify=siemplify,
        param_name="Environments",
        is_mandatory=True,
        print_value=True,
        default_value="Default Environment",
    )

    product_names = extract_action_param(
        siemplify=siemplify,
        param_name="Products",
        is_mandatory=True,
        print_value=True,
        default_value="Vectra QUX",
    )

    try:
        all_cases = True
        if hours_backwards:
            hours_backwards = validate_integer(
                hours_backwards,
                field_name="Max Hours Backwards",
                zero_allowed=True,
            )
            if hours_backwards != 0:
                all_cases = False

        environments = [env.strip() for env in environments.split(",") if env.strip()]
        product_names = [
            product.strip() for product in product_names.split(",") if product.strip()
        ]

        # Check if required fields are provided or not
        if not (environments and product_names):
            raise VectraQUXException(
                "The required parameter values cannot be empty. Please provide values for the following required parameters: ['Environments', 'Products'].",
            )

        cases_last_success_timestamp = get_last_success_time_for_job(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
            timestamp_key=CASES_TIMESTAMP_DB_KEY,
        )

        clear_empty_cases(
            siemplify,
            cases_last_success_timestamp,
            all_cases,
            environments=environments,
            product_names=product_names,
        )

        save_timestamp_for_job(
            siemplify,
            timestamp_key=CASES_TIMESTAMP_DB_KEY,
        )

    except InvalidIntegerException as e:
        siemplify.LOGGER.error("Error while checking hours_backwards")
        siemplify.LOGGER.exception(e)
        raise
    except VectraQUXException as e:
        siemplify.LOGGER.error(
            f"Exception occured while performing Vectra RUX Job {JOB_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
        raise
    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {JOB_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
