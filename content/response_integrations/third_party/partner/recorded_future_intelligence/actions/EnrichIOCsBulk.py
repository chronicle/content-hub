############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from constants import (
    DEFAULT_DEVICE_VENDOR,
    ENRICH_IOC_SOAR_SCRIPT_NAME,
    PROVIDER_NAME,
)
from RecordedFutureCommon import RecordedFutureCommon
from SiemplifyAction import SiemplifyAction
from SiemplifyDataModel import EntityTypes
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

SUPPORTED_ENTITIES = [
    EntityTypes.HOSTNAME,
    EntityTypes.CVE,
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EntityTypes.DOMAIN,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_IOC_SOAR_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    api_url = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiUrl"
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiKey"
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
        siemplify=siemplify,
        api_url=api_url,
        api_key=api_key,
        verify_ssl=verify_ssl,
    )

    try:
        recorded_future_common.enrich_soar_logic(
            entity_types=SUPPORTED_ENTITIES,
            collective_insights_enabled=collective_insights_enabled,
        )
    except Exception as e:
        siemplify.LOGGER.error(
            "General error performing action {}".format(ENRICH_IOC_SOAR_SCRIPT_NAME)
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("\n----------------- Main - Finished -----------------")


if __name__ == "__main__":
    main()
