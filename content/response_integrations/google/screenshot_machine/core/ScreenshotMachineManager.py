# Copyright 2026 Google LLC
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

import requests

from TIPCommon.base.utils import CreateSession

SCREENSHOT_MACHINE_URL = "http://api.screenshotmachine.com/"
NO_CREDITS = "no_credits"
INVALID_CUSTOMER_KEY = "invalid_key"
ERRORS = {
    "no_credits": (
        "Your account is exhausted, you need/should to buy more fresh screenshots."
    ),
    "invalid_hash": "Provided hash is invalid.",
    "invalid_key": "Specified customer API key is invalid.",
    "invalid_url": (
        "Specified URL is invalid or authorization is required "
        "(401 Unauthorized status code was sent)."
    ),
    "missing_key": "Customer key is missing in your request.",
    "missing_url": "URL parameter is missing in your request.",
    "unsupported": (
        "Free account owners are not allowed to call our API using HTTPS protocol."
    ),
    "system_error": (
        "Generic system error. Oops, sometimes bad things happens in the universe:("
    ),
}


class ScreenshotMachineManagerError(Exception):
    """General Exception for ScreenshotMachine manager."""


class ScreenshotMachineLimitManagerError(Exception):
    """Limit Exception for ScreenshotMachine manager."""


class ScreenshotMachineInvalidAPIKeyManagerError(Exception):
    """Invalid Customer API Key Exception for ScreenshotMachine manager."""


class ScreenshotMachineManager:
    """ScreenshotMachine Manager."""

    def __init__(self, api_key: str, use_ssl: bool = False) -> None:
        self.api_key = api_key
        self.session = CreateSession.create_session()
        self.session.verify = use_ssl

    def test_connectivity(self) -> None:
        """
        Test connectivity to ScreenshotMachine
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.session.get(
            SCREENSHOT_MACHINE_URL,
            params={
                "key": self.api_key,
                "url": "http://google.com",
                "format": "jpg",
                "device": "desktop",
                "dimension": "1024xfull",
                "cacheLimit": 0,
                "delay": 0,
            },
        )

        self.validate_response(response, "Unable to connect to ScreenshotMachine.")

    def get_screenshot(
        self,
        url: str,
        image_format: str = "jpg",
        device: str = "desktop",
        dimension: str = "1024xfull",
        cache_limit: int = 0,
        delay: int = 2000,
    ) -> bytes:
        """Get a screenshot of a URL.

        Args:
            url: The url to capture
            image_format: Format of the thumbnail or screenshot.
                Default value is jpg. Available values are: jpg, png, gif
            device: You can capture the web page using various devices
                There are three options available: desktop, phone, tablet.
                Default value is desktop.
            dimension: Size of the thumbnail or screenshot in format [width]x[height].
            cache_limit: Using cacheLimit parameter, you can manage how old (in days)
                cached images do you accept. Default value is 14.
            delay: Using delay parameter, you can manage how long capturing engine
                should wait before the screenshot is created. Default value is 200.
                This parameter is useful when you want to capture a webpage with some
                fancy animation and you want to wait until the animation finish.

        Examples:
            dimension examples:
                320x240 - screenshot size 320x240 pixels
                800x600 - screenshot size 800x600 pixels
                1024x768 - screenshot size 1024x768 pixels
                1920x1080 - screenshot size 1920x1080 pixels
                1024xfull - full page screenshot with width equals to 1024 pixels
                            (can be pretty long)

        Returns:
            The content of the created screenshot
        """
        response = self.session.get(
            SCREENSHOT_MACHINE_URL,
            params={
                "key": self.api_key,
                "url": url,
                "format": image_format,
                "device": device,
                "dimension": dimension,
                "cacheLimit": cache_limit,
                "delay": delay,
            },
        )

        self.validate_response(response, f"Unable to get screenshot of {url}")

        return response.content

    @staticmethod
    def validate_response(
        response: requests.Response,
        error_msg: str = "An error occurred",
    ) -> None:
        """Validate responses from screenshot machine.

        Besides status, it checks the response header for errors.
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise ScreenshotMachineManagerError(
                f"{error_msg}: {error} {error.response.content}"
            ) from error

        error = response.headers.get("X-Screenshotmachine-Response")

        if error == NO_CREDITS:
            # No credits left - raise special exception
            raise ScreenshotMachineLimitManagerError(ERRORS[error])

        elif error == INVALID_CUSTOMER_KEY:
            # Invalid customer API key
            raise ScreenshotMachineInvalidAPIKeyManagerError(ERRORS[error])

        elif error:
            # Error message exists - raise it
            raise ScreenshotMachineManagerError(ERRORS[error])
