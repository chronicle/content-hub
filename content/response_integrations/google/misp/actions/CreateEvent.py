from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.exceptions import MISPNotAcceptableNumberOrStringError, MISPManagerCreateEventError
from ..core.constants import (
    INTEGRATION_NAME,
    CREATE_EVENT_SCRIPT_NAME,
    DISTRIBUTION,
    COMMUNITY,
    THREAT_LEVEL,
    HIGH,
    ANALYSIS,
    INITIAL,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_EVENT_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )
    api_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    # INIT ACTION PARAMETERS:
    event_name = extract_action_param(
        siemplify, param_name="Event Name", is_mandatory=True, print_value=True
    )
    distribution = extract_action_param(
        siemplify,
        param_name="Distribution",
        print_value=True,
        default_value=str(DISTRIBUTION[COMMUNITY]),
    )
    threat_level = extract_action_param(
        siemplify,
        param_name="Threat Level",
        print_value=True,
        default_value=str(THREAT_LEVEL[HIGH]),
    )
    analysis = extract_action_param(
        siemplify,
        param_name="Analysis",
        print_value=True,
        default_value=str(ANALYSIS[INITIAL]),
    )
    publish = extract_action_param(
        siemplify,
        param_name="Publish",
        print_value=True,
        input_type=bool,
        default_value=False,
    )
    comment = extract_action_param(siemplify, param_name="Comment", print_value=True)

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    is_published_successfully = False
    output_message = ""

    try:
        if distribution.lower() not in map(
            str, tuple(DISTRIBUTION.keys()) + tuple(DISTRIBUTION.values())
        ):
            raise MISPNotAcceptableNumberOrStringError(
                "Distribution",
                acceptable_strings=DISTRIBUTION.keys(),
                acceptable_numbers=DISTRIBUTION.values(),
            )
        distribution = int(
            DISTRIBUTION[distribution.lower()]
            if not distribution.isdigit()
            else distribution
        )

        if threat_level.lower() not in map(
            str, tuple(THREAT_LEVEL.keys()) + tuple(THREAT_LEVEL.values())
        ):
            raise MISPNotAcceptableNumberOrStringError(
                "Threat Level",
                acceptable_strings=THREAT_LEVEL.keys(),
                acceptable_numbers=THREAT_LEVEL.values(),
            )
        threat_level = int(
            THREAT_LEVEL[threat_level.lower()]
            if not threat_level.isdigit()
            else threat_level
        )

        if analysis.lower() not in map(
            str, tuple(ANALYSIS.keys()) + tuple(ANALYSIS.values())
        ):
            raise MISPNotAcceptableNumberOrStringError(
                "Analysis",
                acceptable_strings=ANALYSIS.keys(),
                acceptable_numbers=ANALYSIS.values(),
            )
        analysis = int(
            ANALYSIS[analysis.lower()] if not analysis.isdigit() else analysis
        )

        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)

        siemplify.LOGGER.info(f"Creating new event in {INTEGRATION_NAME}")
        event = manager.create_event(
            event_name=event_name,
            distribution=distribution,
            analysis=analysis,
            threat_level=threat_level,
            comment=comment,
        )
        event_id = event.id
        siemplify.LOGGER.info(
            f"Successfully created event {event_id} in {INTEGRATION_NAME}."
        )

        if publish:
            try:
                siemplify.LOGGER.info(
                    f"Publishing event {event_id} in {INTEGRATION_NAME}"
                )
                event = manager.publish_event(event_id=event_id)
                is_published_successfully = True
                siemplify.LOGGER.info(
                    f"Successfully published event {event_id} in {INTEGRATION_NAME}."
                )

            except Exception as error:
                result_value = False
                output_message = f"Event {event_id} was created, but it wasn't published. Reason: {error}"
                siemplify.LOGGER.error(output_message)
                siemplify.LOGGER.exception(error)

        if (publish and is_published_successfully) or not publish:
            output_message = (
                f"Successfully created event {event_id} in {INTEGRATION_NAME}."
            )

        result_value = event_id
        siemplify.result.add_result_json(event.to_json())
    except MISPManagerCreateEventError:
        output_message = (
            f"Action wasn’t able to create new event in {INTEGRATION_NAME}."
        )
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f"Error executing action '{CREATE_EVENT_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
