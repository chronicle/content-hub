from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param

from ..core.base_action import GOQRBaseAction
from ..core.constants import (
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_ERROR_CORRECTION,
    DEFAULT_FOREGROUND_COLOR,
    DEFAULT_IMAGE_FORMAT,
    DEFAULT_MARGIN,
    DEFAULT_QR_SIZE,
    ERROR_CORRECTION_MAPPING,
    GENERATE_QR_CODE_SCRIPT_NAME,
)
from ..core.utils import sanitize_string

if TYPE_CHECKING:
    from typing import NoReturn


class GenerateQrCode(GOQRBaseAction):
    def __init__(self) -> None:
        super().__init__(GENERATE_QR_CODE_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.data = extract_action_param(
            self.soar_action,
            param_name="Content",
            is_mandatory=True,
            print_value=True,
        )
        self.params.size = extract_action_param(
            self.soar_action,
            param_name="Size",
            default_value=DEFAULT_QR_SIZE,
            print_value=True,
        )
        self.params.image_format = extract_action_param(
            self.soar_action,
            param_name="Image Format",
            default_value=DEFAULT_IMAGE_FORMAT,
            print_value=True,
        )
        self.params.error_correction = ERROR_CORRECTION_MAPPING.get(
            extract_action_param(
                self.soar_action,
                param_name="Error Correction",
                default_value=DEFAULT_ERROR_CORRECTION,
                print_value=True,
            )
        )
        self.params.margin = extract_action_param(
            self.soar_action,
            param_name="Margin",
            default_value=DEFAULT_MARGIN,
            input_type=int,
            print_value=True,
        )
        self.params.foreground_color = extract_action_param(
            self.soar_action,
            param_name="Foreground Color",
            default_value=DEFAULT_FOREGROUND_COLOR,
            print_value=True,
        )
        self.params.background_color = extract_action_param(
            self.soar_action,
            param_name="Background Color",
            default_value=DEFAULT_BACKGROUND_COLOR,
            print_value=True,
        )

    def _perform_action(self, *args, **kwargs) -> None:
        qr_code_bytes = self.api_client.generate_qr_code(
            data=self.params.data,
            size=self.params.size,
            image_format=self.params.image_format,
            error_correction=self.params.error_correction,
            margin=self.params.margin,
            foreground_color=self.params.foreground_color,
            background_color=self.params.background_color,
        )

        attachment_name = (
            f"qr_code_{sanitize_string(self.params.data[:20])}.{self.params.image_format}"
        )
        attachment_path: Path = self.save_temp_file(attachment_name, qr_code_bytes)
        json_result = {
            "qr_image_base64_blob": base64.b64encode(qr_code_bytes).decode("utf-8"),
            "size": self.params.size,
            "format": self.params.image_format,
            "error_correction": self.params.error_correction,
            "margin": self.params.margin,
            "foreground_color": self.params.foreground_color,
            "background_color": self.params.background_color,
            "case_attachment_name": attachment_name,
        }
        self.json_results = json_result
        self.soar_action.add_attachment(str(attachment_path))
        self.result_value = True
        self.output_message = "Successfully generated QR code and attached it to the case wall."
        self.soar_action.remove_temp_folder()


def main() -> NoReturn:
    GenerateQrCode().run()


if __name__ == "__main__":
    main()
