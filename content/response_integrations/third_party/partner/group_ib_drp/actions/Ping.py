from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED, EXECUTION_STATE_TIMEDOUT

# Import Managers
from ..core.config import Config
from ..core.UtilsManager import GIBConnector


@output_handler
def main() -> None:
    """Verify connectivity to the Group-IB DRP API.

    Initializes a SiemplifyAction, builds a configured DRP poller via
    ``GIBConnector.init_action_poller`` (which reads the integration's
    configuration parameters, including ``Verify SSL``) and issues a low-cost
    GET request against the ``violation/list`` endpoint. If the call succeeds
    the action ends with ``EXECUTION_STATE_COMPLETED`` and a success message
    in the standard marketplace format; if it fails the exception is logged
    and the action ends with ``EXECUTION_STATE_FAILED``.
    """
    siemplify = SiemplifyAction()

    # Google Chronicle base class set up
    siemplify.script_name = Config.GC_PING

    # Get poller
    poller = GIBConnector(siemplify).init_action_poller()

    # # TEST
    # GIBConnector(siemplify).entity_processor()

    output_message = "Successfully connected to the Group-IB DRP server with the provided connection parameters!"
    connectivity_result = True
    status = EXECUTION_STATE_COMPLETED
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        poller.send_request(endpoint="violation/list", params={"q": None})
        siemplify.LOGGER.info("Connection to API established, performing action {}".format(Config.GC_PING))

    except Exception as e:
        output_message = "Failed to connect to the Group-IB DRP server! Error is {}".format(e)
        connectivity_result = False
        siemplify.LOGGER.error("Connection to API failed, performing action {}".format(Config.GC_PING))
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
