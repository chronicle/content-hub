from __future__ import annotations
from typing import NoReturn

from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from screenshot_machine.core.ScreenshotMachineManager import ScreenshotMachineManager


@output_handler
def main() -> NoReturn:
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("ScreenshotMachine")
    api_key = conf.get("API Key")
    use_ssl = conf.get("Use SSL", "False").lower() == "true"

    screenshot_machine_manager = ScreenshotMachineManager(api_key, use_ssl=use_ssl)

    # Test connectivity
    screenshot_machine_manager.test_connectivity()
    siemplify.end("Connected successfully.", "true")


if __name__ == "__main__":
    main()
