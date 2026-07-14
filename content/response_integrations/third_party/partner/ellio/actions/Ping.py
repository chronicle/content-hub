"""ELLIO - Ping. Validates the integration configuration (mandatory action)."""
from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.action_utils import config_reader
from ..core.constants import DEFAULT_ELLIO_API_ROOT, INTEGRATION_NAME
from ..core.ellio_manager import EllioManager, EllioManagerError

SCRIPT_NAME = "Ping"


@output_handler
def main() -> None:
    """Validate connectivity to the ELLIO API."""
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"

    cfg = config_reader(siemplify)
    ellio_api_root = cfg(param_name="API Root", default_value=DEFAULT_ELLIO_API_ROOT, input_type=str)
    ellio_api_key = cfg(param_name="API Key", is_mandatory=True, input_type=str)
    verify_ssl = cfg(param_name="Verify SSL", default_value=True, input_type=bool)

    manager = EllioManager(ellio_api_root=ellio_api_root, ellio_api_key=ellio_api_key, verify_ssl=verify_ssl)
    try:
        manager.test_connectivity()
    except EllioManagerError as error:
        siemplify.end(f"Failed to connect to the ELLIO server! Error is {error}",
                      False, EXECUTION_STATE_FAILED)
        return
    siemplify.end("Successfully connected to the ELLIO server with the provided connection parameters!",
                  True, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
