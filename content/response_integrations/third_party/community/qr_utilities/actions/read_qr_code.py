from __future__ import annotations

import os
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param

from ..core.base_action import QrUtilitiesBaseAction
from ..core.constants import READ_QR_CODE_SCRIPT_NAME
from ..core.exceptions import QrUtilitiesError

if TYPE_CHECKING:
    from typing import NoReturn


class ReadQrCode(QrUtilitiesBaseAction):
    def __init__(self) -> None:
        super().__init__(READ_QR_CODE_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.file_path = extract_action_param(
            self.soar_action,
            param_name="File Path",
            is_mandatory=True,
            print_value=True,
        )

    def _perform_action(self, *args, **kwargs) -> None:
        file_path = self.params.file_path
        if not os.path.exists(file_path):
            raise QrUtilitiesError(f"File not found at path: {file_path}")

        with open(file_path, "rb") as f:
            decoded_results = self.api_client.read_qr_code(f)

        if not decoded_results:
            raise QrUtilitiesError("Could not decode QR code from the provided image.")

        # Set JSON result for the action
        self.json_results = {
            "decoded_qr_codes": [result.to_json() for result in decoded_results]
        }

        # For the output message, we'll just use the data from the very first symbol found.
        first_data = decoded_results[0].first_symbol_data
        if first_data:
            self.output_message = f"Successfully decoded QR code. Data: {first_data}"
        else:
            self.output_message = (
                "Successfully read QR code, but no data was found in the primary symbol."
            )

        self.result_value = True


def main() -> NoReturn:
    ReadQrCode().run()


if __name__ == "__main__":
    main()
