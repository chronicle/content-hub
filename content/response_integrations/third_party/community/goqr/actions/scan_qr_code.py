from __future__ import annotations

import base64
import binascii
import io
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param

from ..core.base_action import GOQRBaseAction
from ..core.constants import SCAN_QR_CODE_SCRIPT_NAME
from ..core.exceptions import GOQRError

if TYPE_CHECKING:
    from typing import Never, NoReturn


class ScanQrCode(GOQRBaseAction):
    def __init__(self) -> None:
        super().__init__(SCAN_QR_CODE_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.qr_base64_blob = extract_action_param(
            self.soar_action,
            param_name="QR Image Base64 Blob",
            is_mandatory=True,
            print_value=False,
        )

    def _perform_action(self, _: Never) -> None:
        base64_blob = self.params.qr_base64_blob

        try:
            image_bytes = base64.b64decode(base64_blob)
        except binascii.Error as e:
            raise GOQRError(
                "Failed to decode Base64 string. Please ensure you are providing a valid "
                f"Base64-encoded image blob. Error: {e}"
            )

        image_file = io.BytesIO(image_bytes)
        decoded_results = self.api_client.read_qr_code(image_file)

        if not decoded_results or not decoded_results[0].symbols:
            raise GOQRError(
                "Unable to decode the readable QR code data. The uploaded file may not be a "
                "valid or recognizable QR code image."
            )

        first_symbol = decoded_results[0].symbols[0]

        if first_symbol.error:
            raise GOQRError(f"The API could not decode the QR code. Error: {first_symbol.error}")

        if first_symbol.data:
            self.output_message = "Successfully decoded QR code from provided image content."
            self.json_results = {
                "decoded_qr_codes": [result.to_json() for result in decoded_results]
            }
            self.result_value = True

        else:
            raise GOQRError(
                "Successfully read provided image content, but no QR code data was found in the "
                "primary symbol."
            )


def main() -> NoReturn:
    ScanQrCode().run()


if __name__ == "__main__":
    main()
