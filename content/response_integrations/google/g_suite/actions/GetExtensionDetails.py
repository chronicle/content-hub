from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator
from g_suite.core import consts
from g_suite.core import datamodels
from g_suite.core.action_init import create_api_client
from g_suite.core.GSuiteManager import GSuiteManager
from g_suite.core.exceptions import GSuiteNotFoundException

if TYPE_CHECKING:
    from typing import Any
    from TIPCommon.types import JSON


class GetExtensionDetailsAction(Action):

    def __init__(self) -> None:
        super().__init__(consts.GET_EXTENSION_DETAILS_SCRIPT_NAME)
        self.manager: GSuiteManager | None = None
        self.output_message: str = ""
        self.result_value: bool = False
        self.json_results: list = []

    def _init_api_clients(self) -> None:
        self.manager: GSuiteManager = create_api_client(self.soar_action)

    def _extract_action_parameters(self) -> None:
        raw_extension_ids = extract_action_param(
            self.soar_action,
            param_name="Extension ID",
            is_mandatory=True,
            print_value=True,
        )

        self.params.extension_ids = string_to_multi_value(
            string_value=raw_extension_ids,
        )

        self.params.max_users = extract_action_param(
            self.soar_action,
            param_name="Max Requesting Users To Return",
            is_mandatory=True,
            print_value=True,
            default_value=consts.MAX_USERS_ALLOWED,
            input_type=int,
        )
        self.params.max_devices = extract_action_param(
            self.soar_action,
            param_name="Max Requesting Devices To Return",
            is_mandatory=True,
            print_value=True,
            default_value=consts.MAX_USERS_ALLOWED,
            input_type=int,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)

        validator.validate_range(
            param_name="Max Requesting Users To Return",
            value=self.params.max_users,
            min_limit=consts.MINIMUM_POSITIVE_INTEGER,
            max_limit=consts.MAX_RESULTS_ALLOWED,
        )
        validator.validate_range(
            param_name="Max Requesting Devices To Return",
            value=self.params.max_devices,
            min_limit=consts.MINIMUM_POSITIVE_INTEGER,
            max_limit=consts.MAX_RESULTS_ALLOWED,
        )

    def _perform_action(self, _: Any = None) -> None:
        (
            successful_extensions,
            failed_extensions,
            json_results,
        ) = self._process_extensions()
        self._process_results(successful_extensions, failed_extensions, json_results)

    def _process_extensions(self) -> tuple[list[str], list[str], list[JSON]]:
        successful_extensions: list[str] = []
        failed_extensions: list[str] = []
        json_results: list[JSON] = []

        for extension_id in self.params.extension_ids:
            self.logger.info(
                f"Fetching details for extension: {extension_id}"
            )
            try:
                display_name, extension_info = self._get_full_extension_info(
                    extension_id
                )

                if display_name and extension_info:
                    json_results.append(
                        {"Entity": display_name, "EntityResult": extension_info}
                    )
                    successful_extensions.append(display_name)
                else:
                    failed_extensions.append(extension_id)
                    self.logger.info(
                        "Could not retrieve full details for extension with ID: "
                        f"{extension_id}"
                    )

            except GSuiteNotFoundException:
                failed_extensions.append(extension_id)
                self.logger.info(
                    f"Could not find extension with ID: {extension_id}"
                )

        return successful_extensions, failed_extensions, json_results

    def _get_full_extension_info(
        self,
        extension_id: str,
    ) -> tuple[str | None, JSON | None]:
        details: datamodels.ExtensionDetails = self.manager.get_extension_details(
            extension_id=extension_id
        )
        users: list[datamodels.RequestingUser] = (
            self.manager.get_extension_requesting_users(
                extension_id=extension_id,
                page_size=self.params.max_users,
            )
        )
        devices: list[datamodels.RequestingDevice] = (
            self.manager.get_extension_requesting_devices(
                extension_id=extension_id,
                page_size=self.params.max_devices,
            )
        )

        self.logger.info(
            f"Successfully fetched details for extension: {extension_id}"
        )

        extension_json: JSON = self._build_extension_json(details, users, devices)

        return details.display_name, extension_json

    def _build_extension_json(
        self,
        details: datamodels.ExtensionDetails,
        users: list[datamodels.RequestingUser],
        devices: list[datamodels.RequestingDevice],
    ) -> JSON:
        extension_json: JSON = details.to_json()
        chrome_app_info: JSON = extension_json.setdefault("chromeAppInfo", {})

        chrome_app_info["requestingUserDetails"] = [user.to_json() for user in users]
        chrome_app_info["requestingDeviceDetails"] = [
            {"device": device.device_name, "justification": device.justification}
            for device in devices
        ]

        return extension_json

    def _process_results(
        self,
        successful_extensions: list[str],
        failed_extensions: list[str],
        json_results: list[JSON],
    ) -> None:
        self.result_value = bool(successful_extensions)

        if successful_extensions:
            output_messages: list[str] = [
                "Successfully returned information about the following extensions in "
                f"Google Workspace: {', '.join(successful_extensions)}."
            ]
            self.json_results = json_results

            if failed_extensions:
                output_messages.append(
                    "Action wasn’t able to return information about the following "
                    "extensions in Google Workspace: "
                    f"{', '.join(failed_extensions)}."
                )

            self.output_message = "\n".join(output_messages)
        else:
            self.output_message = (
                "No information about the provided extensions were found."
            )


def main() -> None:
    action = GetExtensionDetailsAction()
    action.run()


if __name__ == "__main__":
    main()
