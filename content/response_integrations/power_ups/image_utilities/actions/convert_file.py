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

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pdf2image import convert_from_path
from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError,
)
from PIL import Image, UnidentifiedImageError
from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

from ..core.constants import (
    CONVERT_FILE_SCRIPT_NAME,
    PDF_FORMAT,
    PNG_FORMAT,
    RGB_FORMAT,
)
from ..core.exceptions import ParameterNotFoundError
from ..core.utils import ensure_remote_agent

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Never


class ConvertFileAction(Action):
    """Convert files between PNG and PDF formats."""

    def __init__(self) -> None:
        """Initialize the Convert File action."""
        super().__init__(CONVERT_FILE_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.input_file_format = extract_action_param(
            siemplify=self.soar_action,
            param_name="Input File Format",
            is_mandatory=True,
            print_value=True,
        )
        self.params.input_file_path = extract_action_param(
            siemplify=self.soar_action,
            param_name="Input File Path",
            is_mandatory=True,
            print_value=True,
        )
        self.params.output_file_format = extract_action_param(
            siemplify=self.soar_action,
            param_name="Output File Format",
            is_mandatory=True,
            print_value=True,
        )

    def _init_api_clients(self) -> None:
        """Initialize API clients if needed."""

    def _validate_params(self) -> None:
        ensure_remote_agent(self.soar_action, CONVERT_FILE_SCRIPT_NAME)

        validator: ParameterValidator = ParameterValidator(self.soar_action)

        input_path: Path = Path(self.params.input_file_path)
        if not input_path.exists():
            error_msg: str = f"Source file not found: {input_path}"
            raise ParameterNotFoundError(error_msg)

        self.params.input_file_format = validator.validate_ddl(
            param_name="Input File Format",
            value=self.params.input_file_format,
            ddl_values=[PNG_FORMAT, PDF_FORMAT],
        )

        self.params.output_file_format = validator.validate_ddl(
            param_name="Output File Format",
            value=self.params.output_file_format,
            ddl_values=[PNG_FORMAT, PDF_FORMAT],
        )

        if self.params.input_file_format == self.params.output_file_format:
            error_msg: str = "Input and output file formats cannot be the same."
            raise ParameterNotFoundError(error_msg)

    def _perform_action(self, _: Never) -> None:
        output_path: str = self._build_output_path()

        converter: Callable[[str], str | None] = (
            self._convert_pdf_to_png
            if self.params.output_file_format == PNG_FORMAT
            else self._convert_png_to_pdf
        )

        result_path: str | None = converter(output_path)

        if not result_path:
            self.result_value = False
            self.output_message = "No output file was created. Check logs and parameters."
            return

        self.json_results = [
            {
                "output_format": self.params.output_file_format,
                "file_path": result_path,
            },
        ]
        self.output_message = "Successfully converted file."

    def _build_output_path(self) -> str:
        input_path: Path = Path(self.params.input_file_path)
        output_dir: Path = Path(tempfile.gettempdir())
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_filename = f"{input_path.stem}_{timestamp}.{self.params.output_file_format.lower()}"

        return str(output_dir / output_filename)

    def _convert_pdf_to_png(self, output_path: str) -> str | None:
        if not shutil.which("pdftoppm"):
            error_msg: str = "Dependency 'pdftoppm' is missing. Install 'poppler-utils'."
            raise ParameterNotFoundError(error_msg)

        self.logger.info(f"Converting PDF '{self.params.input_file_path}' → PNG '{output_path}'")

        try:
            images = convert_from_path(self.params.input_file_path)

            if not images:
                self.logger.warning(f"No images extracted from PDF '{self.params.input_file_path}'")
                return None

            images[0].save(output_path, PNG_FORMAT)
            return output_path

        except (PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError) as e:
            error_msg: str = f"PDF processing error: {e}"
            raise ParameterNotFoundError(error_msg) from e

        except OSError as e:
            error_msg: str = f"Failed to save PNG file: {e}"
            raise ParameterNotFoundError(error_msg) from e

    def _convert_png_to_pdf(self, output_path: str) -> str | None:
        self.logger.info(f"Converting PNG '{self.params.input_file_path}' → PDF '{output_path}'")

        try:
            with Image.open(self.params.input_file_path) as img:
                img.convert(RGB_FORMAT).save(output_path)
            return output_path

        except FileNotFoundError as e:
            error_msg: str = f"PNG file not found: {self.params.input_file_path}"
            raise ParameterNotFoundError(error_msg) from e

        except UnidentifiedImageError as e:
            error_msg: str = f"Cannot identify image file: {self.params.input_file_path}"
            raise ParameterNotFoundError(error_msg) from e

        except OSError as e:
            error_msg: str = f"Failed to save PDF file: {e}"
            raise ParameterNotFoundError(error_msg) from e


def main() -> None:
    """Run the Convert File action."""
    ConvertFileAction().run()


if __name__ == "__main__":
    main()
