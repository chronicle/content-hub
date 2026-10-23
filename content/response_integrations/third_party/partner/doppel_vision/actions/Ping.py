from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.config import create_manager_from_siemplify
from ..core.exceptions import DoppelError

SCRIPT_NAME = "Ping"


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    try:
        doppel_manager = create_manager_from_siemplify(siemplify)
        doppel_manager.connection_test()
        siemplify.end(
            f"Successfully connected to the Doppel Vision server using API "
            f"{doppel_manager.api_version} with the provided connection parameters!",
            True,
        )
    except DoppelError as e:
        siemplify.end(
            f"Failed to connect to the Doppel Vision server: {e}",
            False,
        )
    except Exception as e:
        siemplify.end(
            f"Failed to connect to the Doppel Vision server: {e!s}",
            False,
        )


if __name__ == "__main__":
    main()
