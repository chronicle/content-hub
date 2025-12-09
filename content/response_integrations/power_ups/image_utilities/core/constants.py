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

from enum import Enum

INTEGRATION_NAME: str = "Image Utilities"
PING_SCRIPT_NAME: str = "Ping"
OCR_IMAGE_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - OCR Image"
RASTERIZE_CONTENT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Rasterize Content"
CONVERT_FILE_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Convert File"

UTF8_ENCODING: str = "utf-8"
RASTERIZE_ACTION_DELAY_TIME: int = 5
DEFAULT_RASTERIZE_WIDTH: int = 1920
DEFAULT_RASTERIZE_HEIGHT: int = 1080
DEFAULT_RASTERIZE_TIMEOUT: int = 120
MIN_LIMIT: int = 1
RASTERIZE_HTML_PREFIX: str = "<html><body><pre>"
RASTERIZE_HTML_SUFFIX: str = "</pre></body></html>"
PLAYWRIGHT_PACKAGE_ERROR: str = "Executable doesn't exist at"
PNG_FORMAT: str = "PNG"
PDF_FORMAT: str = "PDF"
RGB_FORMAT: str = "RGB"


class DDLEnum(Enum):
    """Base class for DDL enums."""

    @classmethod
    def values(cls) -> list[str]:
        """Get a list of values for the enum.

        Returns:
            list[str]: A list of values for the enum.

        """
        return [item.value for item in cls]


class InputType(DDLEnum):
    """Enum for input types."""

    URL = "URL"
    HTML = "HTML"
    EMAIL = "Email"


class OutputType(DDLEnum):
    """Enum for output types."""

    PNG = "PNG"
    PDF = "PDF"
    BOTH = "Both"


class ExportMethod(DDLEnum):
    """Enum for export methods."""

    CASE_ATTACHMENT = "Case Attachment"
    FILE_PATH = "File Path"
    BOTH = "Both"


class PlaywrightWaitUntil(DDLEnum):
    """Enum for Playwright's `wait_until` options."""

    LOAD = "LOAD"
    DOM_CONTENT_LOADED = "DOM_CONTENT_LOADED"
    NETWORK_IDLE = "NETWORK_IDLE"
    COMMIT = "COMMIT"
