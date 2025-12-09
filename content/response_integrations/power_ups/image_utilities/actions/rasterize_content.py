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

import asyncio
import hashlib
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from playwright.async_api import ViewportSize, async_playwright
from TIPCommon.base.action import Action
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.exceptions import ActionSetupError
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator

from ..core.constants import (
    DEFAULT_RASTERIZE_HEIGHT,
    DEFAULT_RASTERIZE_TIMEOUT,
    DEFAULT_RASTERIZE_WIDTH,
    MIN_LIMIT,
    PLAYWRIGHT_PACKAGE_ERROR,
    RASTERIZE_ACTION_DELAY_TIME,
    RASTERIZE_CONTENT_SCRIPT_NAME,
    RASTERIZE_HTML_PREFIX,
    RASTERIZE_HTML_SUFFIX,
    UTF8_ENCODING,
    ExportMethod,
    InputType,
    OutputType,
    PlaywrightWaitUntil,
)
from ..core.exceptions import ParameterNotFoundError
from ..core.utils import ensure_remote_agent

if TYPE_CHECKING:
    from typing import Never, NoReturn

    from playwright.async_api import Browser, BrowserContext, Page, Playwright
    from TIPCommon.base.interfaces.logger import ScriptLogger
    from TIPCommon.data_models import Container


class RasterizeInput(NamedTuple):
    """Represents the input for rasterization."""

    html_content: str
    inputs: list[str]


class RasterizeResult(NamedTuple):
    """Represents the result of rasterization."""

    all_created_files: list[str]
    successful_inputs: list[str]
    failed_inputs: list[str]


class RasterizeAction(Action):
    """Rasterize Content action."""

    def __init__(self) -> None:
        """Initialize the RasterizeAction."""
        super().__init__(RASTERIZE_CONTENT_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.input_type = extract_action_param(
            siemplify=self.soar_action,
            param_name="Input Type",
            is_mandatory=True,
            print_value=True,
        )
        self.params.input_data = extract_action_param(
            siemplify=self.soar_action,
            param_name="URLs or Body",
            is_mandatory=True,
            print_value=True,
        )
        self.params.output_type = extract_action_param(
            siemplify=self.soar_action,
            param_name="Output Type",
            default_value=OutputType.PNG.value,
            print_value=True,
        )
        self.params.export_method = extract_action_param(
            siemplify=self.soar_action,
            param_name="Export Method",
            default_value=ExportMethod.CASE_ATTACHMENT.value,
            print_value=True,
        )
        self.params.height = extract_action_param(
            siemplify=self.soar_action,
            param_name="Height",
            default_value=DEFAULT_RASTERIZE_HEIGHT,
            input_type=int,
            print_value=True,
        )
        self.params.width = extract_action_param(
            siemplify=self.soar_action,
            param_name="Width",
            default_value=DEFAULT_RASTERIZE_WIDTH,
            input_type=int,
            print_value=True,
        )
        self.params.timeout: int = extract_action_param(
            siemplify=self.soar_action,
            param_name="Timeout",
            default_value=DEFAULT_RASTERIZE_TIMEOUT,
            input_type=int,
            print_value=True,
        )
        self.params.full_screen: bool = extract_action_param(
            siemplify=self.soar_action,
            param_name="Full Screen",
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        self.params.wait_until: str = extract_action_param(
            siemplify=self.soar_action,
            param_name="Wait For",
            default_value=PlaywrightWaitUntil.NETWORK_IDLE.value,
            print_value=True,
        )
        self.params.wait_for_selector: str = extract_action_param(
            siemplify=self.soar_action,
            param_name="Wait for Selector",
            print_value=True,
        )

    def _init_api_clients(self) -> None:
        """Initialize API clients if needed."""

    def _validate_params(self) -> None:
        ensure_remote_agent(self.soar_action, RASTERIZE_CONTENT_SCRIPT_NAME)

        validator: ParameterValidator = ParameterValidator(self.soar_action)
        self.params.input_type = validator.validate_ddl(
            "Input Type",
            self.params.input_type,
            InputType.values(),
        )
        self.params.output_type = validator.validate_ddl(
            "Output Type",
            self.params.output_type,
            OutputType.values(),
        )
        self.params.export_method = validator.validate_ddl(
            "Export Method",
            self.params.export_method,
            ExportMethod.values(),
        )
        self.params.wait_until = validator.validate_ddl(
            "Wait For",
            self.params.wait_until,
            PlaywrightWaitUntil.values(),
        )
        self.params.timeout = validator.validate_range(
            "Timeout",
            self.params.timeout,
            MIN_LIMIT,
            DEFAULT_RASTERIZE_TIMEOUT,
        )
        self.params.height = validator.validate_lower_limit(
            "Height",
            self.params.height,
            MIN_LIMIT,
        )
        self.params.width = validator.validate_lower_limit(
            "Width",
            self.params.width,
            MIN_LIMIT,
        )
        if self.params.full_screen:
            self.logger.info(
                "Full Screen is enabled. 'Height' and 'Width' parameters "
                "will be ignored for the screenshot.",
            )

    def _perform_action(self, _: Never) -> None:
        rasterize_input = self._prepare_rasterize_inputs()
        rasterize_result = self._rasterize_inputs(rasterize_input)

        self.result_value = bool(rasterize_result.successful_inputs)
        self.output_message = self._build_output_message(rasterize_input, rasterize_result)

        if rasterize_result.all_created_files:
            self.json_results = self._process_rasterize_outputs(rasterize_result.all_created_files)

        time.sleep(RASTERIZE_ACTION_DELAY_TIME)

    def _prepare_rasterize_inputs(self) -> RasterizeInput:
        """Prepare inputs for rasterization based on the input type."""
        html_content: str = self._get_html_content()
        inputs = (
            string_to_multi_value(self.params.input_data, only_unique=True)
            if self.params.input_type == InputType.URL.value
            else [self.params.input_data]
        )
        return RasterizeInput(html_content=html_content, inputs=inputs)

    def _get_html_content(self) -> str:
        """Get HTML content based on the input type."""
        if self.params.input_type == InputType.URL.value:
            return ""

        if self.params.input_type == InputType.HTML.value:
            return self.params.input_data

        if self.params.input_type == InputType.EMAIL.value:
            return f"{RASTERIZE_HTML_PREFIX}{self.params.input_data}{RASTERIZE_HTML_SUFFIX}"

        error_msg: str = f"Invalid Input Type: {self.params.input_type}"
        raise ParameterNotFoundError(error_msg)

    def _rasterize_inputs(self, rasterize_input: RasterizeInput) -> RasterizeResult:
        """Rasterize the provided inputs and return the result.

        This method launches Playwright once and uses the Rasterizer helper to
        rasterize each input. The public synchronous API is preserved by
        running the async orchestration via ``asyncio.run``.
        """
        return asyncio.run(self._rasterize_with_playwright(rasterize_input))

    async def _rasterize_with_playwright(self, rasterize_input: RasterizeInput) -> RasterizeResult:
        """Async orchestration that initializes Playwright once and rasterizes inputs."""
        all_created_files: list[str] = []
        successful_inputs: list[str] = []
        failed_inputs: list[str] = []

        rasterizer = Rasterizer(self.params, self.logger)
        try:
            await rasterizer.initialize()

            for item in rasterize_input.inputs:
                try:
                    self.logger.info(f"Processing input: {item}")
                    png_path, pdf_path = self._get_output_paths(item)
                    created_files = await rasterizer.rasterize(
                        item, rasterize_input.html_content, png_path, pdf_path
                    )

                    if created_files:
                        all_created_files.extend(created_files)

                    successful_inputs.append(item)
                    self.logger.info(f"Successfully rasterized input '{item}'.")

                except Exception as e:
                    if PLAYWRIGHT_PACKAGE_ERROR in str(e):
                        error_msg: str = (
                            "Playwright browser binaries not found.\n\n"
                            "To fix this, please install Playwright inside your Debian-based "
                            "Remote Agent container:\n\n"
                            "1. Bash into the container as root:\n"
                            "   podman exec -it -u 0 <container_name> bash\n\n"
                            "2. Install Playwright and Chromium dependencies:\n"
                            "   python3.11 -m pip install playwright\n"
                            "   playwright install --with-deps chromium\n\n"
                            "3. Copy the downloaded browser binaries from root to the agent user:\n"
                            "   cp -r /root/.cache/ms-playwright /home/siemplify_agent/.cache/\n"
                            "   chown -R siemplify_agent:siemplify_agent /home/siemplify_agent/"
                            ".cache/ms-playwright\n\n"
                            "After completing these steps, re-run the action."
                        )
                        raise ActionSetupError(error_msg) from e

                    self.logger.exception(f"Failed to rasterize input '{item}': {e}")
                    failed_inputs.append(item)

        finally:
            await rasterizer.close()

        return RasterizeResult(all_created_files, successful_inputs, failed_inputs)

    def _get_output_paths(
        self,
        input_item: str,
    ) -> tuple[str | None, str | None]:
        """Generate unique output file paths for PNG and PDF based on the input item."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        case_id = self.soar_action.case_id
        item_hash = hashlib.sha256(input_item.encode(UTF8_ENCODING)).hexdigest()
        base_filename = f"{case_id}_{item_hash}_{timestamp}"

        output_dir: Path = Path(tempfile.gettempdir())

        png_path: str | None = None
        if self.params.output_type in {OutputType.PNG.value, OutputType.BOTH.value}:
            png_path = (output_dir / f"{base_filename}.png").as_posix()

        pdf_path: str | None = None
        if self.params.output_type in {OutputType.PDF.value, OutputType.BOTH.value}:
            pdf_path = (output_dir / f"{base_filename}.pdf").as_posix()

        return png_path, pdf_path

    def _build_output_message(
        self,
        rasterize_input: RasterizeInput,
        rasterize_result: RasterizeResult,
    ) -> str:
        """Build the output message based on rasterization results."""
        if self.params.input_type in {InputType.HTML.value, InputType.EMAIL.value}:
            return (
                "Successfully rasterized content based on the provided input."
                if rasterize_result.successful_inputs
                else "Action wasn't able to rasterize content based on the provided input."
            )

        output_messages: list[str] = []
        if rasterize_result.successful_inputs:
            output_messages.append(
                "Successfully rasterized content based on the following URLs: "
                f"{', '.join(rasterize_result.successful_inputs)}.",
            )

        if rasterize_result.failed_inputs:
            if len(rasterize_result.failed_inputs) == len(rasterize_input.inputs):
                output_messages.append(
                    "Action wasn't able to rasterize content for the provided URLs.",
                )
            else:
                output_messages.append(
                    "Action wasn't able to rasterize content for the following URLs: "
                    f"{', '.join(rasterize_result.failed_inputs)}.",
                )

        return "\n".join(output_messages)

    def _process_rasterize_outputs(
        self,
        all_created_files: list[str],
    ) -> list[dict[str, str | None]]:
        """Process the created raster files based on the export method."""
        json_results: list[dict[str, str | None]] = []
        for file_path in all_created_files:
            path_obj = Path(file_path)
            attachment_name = path_obj.name
            result_file_path: str | None = None

            if self.params.export_method in {
                ExportMethod.CASE_ATTACHMENT.value,
                ExportMethod.BOTH.value,
            }:
                self.logger.info(f"Attaching file '{path_obj.name}' to the case.")
                self._add_attachment_to_current_case(file_path)
                if self.params.export_method == ExportMethod.CASE_ATTACHMENT.value:
                    path_obj.unlink(missing_ok=True)

            if self.params.export_method in {
                ExportMethod.FILE_PATH.value,
                ExportMethod.BOTH.value,
            }:
                result_file_path = file_path

            json_results.append({
                "attachment_name": attachment_name,
                "file_path": result_file_path,
            })
        return json_results


class Rasterizer:
    """Helper that manages a single Playwright browser/context/page lifecycle and
    exposes a simple `rasterize` API for rendering a URL/HTML to PNG/PDF.

    This class is intentionally small and focused so expensive browser startup
    is done once per batch of inputs.
    """

    def __init__(self, params: Container, logger: ScriptLogger) -> None:
        self.params: Container = params
        self.logger: ScriptLogger = logger
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def initialize(self) -> None:
        """Start Playwright, launch browser and create a single page context."""
        # async_playwright().start() returns a Playwright object that needs to
        # be stopped via .stop(). We store it and stop it in `close()`.
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.context = await self.browser.new_context(
            ignore_https_errors=True,
            viewport=ViewportSize(width=self.params.width, height=self.params.height),
        )
        self.page = await self.context.new_page()

    async def rasterize(
        self,
        item: str,
        html_content: str | None,
        png_path: str | None,
        pdf_path: str | None,
    ) -> list[str]:
        """Rasterize a single item using the existing page context."""
        created_files: list[str] = []
        wait_until_value: str = self.params.wait_until.lower().replace("_", "")

        if self.params.input_type == InputType.URL.value:
            self.logger.info(f"Navigating to URL: {item}")
            await self.page.goto(
                item,
                timeout=self.params.timeout * NUM_OF_MILLI_IN_SEC,
                wait_until=wait_until_value,
            )
        elif html_content:
            self.logger.info(f"Setting {self.params.input_type} content for rasterization.")
            await self.page.set_content(
                html_content,
                timeout=self.params.timeout * NUM_OF_MILLI_IN_SEC,
                wait_until=wait_until_value,
            )

        if self.params.wait_for_selector:
            self.logger.info(f"Waiting for selector '{self.params.wait_for_selector}'...")
            await self.page.wait_for_selector(
                self.params.wait_for_selector,
                state="visible",
                timeout=self.params.timeout * NUM_OF_MILLI_IN_SEC,
            )

        if png_path:
            await self._take_screenshot(png_path)
            created_files.append(png_path)

        if pdf_path:
            await self.page.pdf(path=pdf_path)
            created_files.append(pdf_path)

        return created_files

    async def _take_screenshot(self, png_path: str) -> None:
        """Take a screenshot; if full_screen is enabled, adjust viewport height."""
        if self.params.full_screen:
            page_height: int = await self.page.evaluate("document.body.scrollHeight")
            if page_height > 0:
                await self.page.set_viewport_size(
                    ViewportSize(width=self.params.width, height=page_height),
                )
            await self.page.screenshot(path=png_path)
        else:
            await self.page.screenshot(path=png_path, full_page=False)

    async def close(self) -> None:
        """Close browser and stop Playwright runtime."""
        try:
            if self.browser:
                await self.browser.close()
        finally:
            if self.playwright:
                await self.playwright.stop()


def main() -> NoReturn:
    """Run the Rasterize Content action."""
    RasterizeAction().run()


if __name__ == "__main__":
    main()
