############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import (
    DEFAULT_DEVICE_VENDOR,
    DEFAULT_THRESHOLD,
    ENRICH_CVE_SCRIPT_NAME,
    PROVIDER_NAME,
)
from ..core.exceptions import RecordedFutureUnauthorizedError
from ..core.RecordedFutureCommon import RecordedFutureCommon


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_CVE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_url = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="ApiUrl",
    )
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
    collective_insights_global = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="CollectiveInsights",
        default_value=True,
        input_type=bool,
    )

    threshold = extract_action_param(
        siemplify,
        param_name="Risk Score Threshold",
        is_mandatory=True,
        default_value=DEFAULT_THRESHOLD,
        input_type=int,
    )
    include_links = extract_action_param(
        siemplify,
        param_name="Include Links",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    collective_insights_action = extract_action_param(
        siemplify,
        param_name="Enable Collective Insights",
        default_value=True,
        input_type=bool,
    )

    # Exclude Collective Insights submissions for Recorded Future Alerts
    reporting_vendor = siemplify.current_alert.reporting_vendor
    external_vendor = reporting_vendor != DEFAULT_DEVICE_VENDOR

    collective_insights_enabled = (
        collective_insights_action and collective_insights_global and external_vendor
    )

    recorded_future_common = RecordedFutureCommon(
        siemplify,
        api_url,
        api_key,
        verify_ssl=verify_ssl,
    )

    try:
        recorded_future_common.enrich_common_logic(
            [EntityTypes.CVE],
            threshold,
            ENRICH_CVE_SCRIPT_NAME,
            include_links,
            collective_insights_enabled,
        )

    except RecordedFutureUnauthorizedError as e:
        output_message = f"Unauthorized - please check your API token and try again. {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ENRICH_CVE_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("\n----------------- Main - Finished -----------------")


if __name__ == "__main__":
    main()
