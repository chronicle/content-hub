# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import base64
import tempfile
from typing import TYPE_CHECKING

import pytesseract
from PIL import Image
from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param

from ..core.constants import OCR_IMAGE_SCRIPT_NAME
from ..core.exceptions import OcrImageSetupError, ParameterNotFoundError
from ..core.utils import ensure_remote_agent

if TYPE_CHECKING:
    from typing import Never, NoReturn


class OcrImage(Action):
    """OCR Image action."""

    def __init__(self) -> None:
        """Initialize the OCR Image action."""
        super().__init__(OCR_IMAGE_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        """Extract and normalize input parameters."""
        self.params.base64_image = extract_action_param(
            self.soar_action,
            param_name="Base64 Encoded Image",
            print_value=True,
        )
        self.params.file_path = extract_action_param(
            self.soar_action,
            param_name="File Path",
            print_value=True,
        )

    def _validate_params(self) -> None:
        """Validate logical correctness of supplied parameters."""
        param_error_msg: str = 'either "Base64 Encoded Image" or "File Path" needs to have a value.'

        ensure_remote_agent(self.soar_action, OCR_IMAGE_SCRIPT_NAME)

        if not self.params.base64_image and not self.params.file_path:
            raise ParameterNotFoundError(param_error_msg)

    def _init_api_clients(self) -> None:
        """Initialize API clients if needed."""

    def _perform_action(self, _: Never) -> None:
        """Perform OCR on the provided image."""
        text: str
        if self.params.base64_image:
            image_data: bytes = base64.b64decode(self.params.base64_image)
            with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
                tmp.write(image_data)
                tmp.flush()
                text = _extract_text(tmp.name)
        else:
            text = _extract_text(self.params.file_path)

        self.json_results = {"extracted_text": text.strip()}
        self.output_message = "Successfully performed OCR on the provided image."


def _extract_text(file_path: str) -> str:
    """Run OCR and handle missing-Tesseract errors.

    Args:
        file_path: The path of the image file.

    Returns:
        The extracted text from the image.

    """
    tesseract_error_msg: str = (
        "Tesseract OCR engine is not installed in the Remote Agent container.\n\n"
        "To fix this issue, follow these steps:\n"
        "1. Identify and open the Docker/Podman container that runs your Remote Agent.\n"
        "2. Install Tesseract inside that container (Debian-based image):\n"
        "   apt-get update && apt-get install -y tesseract-ocr\n\n"
        "3. Verify that Tesseract is installed by running:\n"
        "   which tesseract\n\n"
        "After installing Tesseract, rerun the 'OCR Image' action."
    )

    try:
        with Image.open(file_path) as img:
            return pytesseract.image_to_string(img)

    except pytesseract.TesseractNotFoundError as e:
        raise OcrImageSetupError(tesseract_error_msg) from e


def main() -> NoReturn:
    """Run the OCR Image action."""
    OcrImage().run()


if __name__ == "__main__":
    main()
