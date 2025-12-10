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

from typing import TYPE_CHECKING

import pytesseract
from playwright.sync_api import sync_playwright
from TIPCommon.base.action import Action
from TIPCommon.exceptions import ActionSetupError

from ..core.constants import PING_SCRIPT_NAME
from ..core.utils import ensure_remote_agent

if TYPE_CHECKING:
    from typing import Never


class Ping(Action):
    """Ping action to validate Remote Agent connectivity and Tesseract availability."""

    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message = (
            "Successfully connected to the Image Utilities server with the provided "
            "connection parameters!"
        )

    def _init_api_clients(self) -> None:
        """Initialize API clients if needed."""

    def _validate_params(self) -> None:
        ensure_remote_agent(self.soar_action, PING_SCRIPT_NAME)

    def _perform_action(self, _: Never) -> None:
        self._verify_tesseract()
        self._verify_playwright()

    def _verify_tesseract(self) -> None:
        """Verify whether tesseract is installed."""
        tesseract_error_msg: str = (
            "Tesseract OCR engine is not installed in the Remote Agent container.\n\n"
            "To fix this issue, follow these steps:\n"
            "1. Identify and open the Docker/Podman container that runs your Remote Agent.\n"
            "2. Install Tesseract inside that container (Debian-based image):\n"
            "   apt-get update && apt-get install -y tesseract-ocr\n\n"
            "3. Verify that Tesseract is installed by running:\n"
            "   which tesseract\n\n"
            "After installing Tesseract, rerun the 'Ping' action."
        )

        try:
            pytesseract.get_tesseract_version()

        except pytesseract.TesseractNotFoundError as e:
            raise ActionSetupError(tesseract_error_msg) from e

    def _verify_playwright(self) -> None:
        """Verify whether playwright is installed."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()

        except Exception as e:
            raise ActionSetupError(
                "Playwright browser binaries not found.\n\n"
                "To fix this, please install Playwright inside your Debian-based "
                "Remote Agent container:\n\n"
                "1. Bash into the container as root:\n"
                "   podman exec -it -u 0 <container_name> bash\n\n"
                "2. Install Playwright and Chromium dependencies:\n"
                "   python3.11 -m pip install playwright==1.56.0\n"
                "   playwright install --with-deps chromium\n\n"
                "3. Copy the downloaded browser binaries from root to the agent user:\n"
                "   cp -r /root/.cache/ms-playwright /home/siemplify_agent/.cache/\n"
                "   chown -R siemplify_agent:siemplify_agent /home/siemplify_agent/"
                ".cache/ms-playwright\n\n"
                "After completing these steps, re-run the action."
            ) from e


def main() -> None:
    Ping().run()


if __name__ == "__main__":
    main()
