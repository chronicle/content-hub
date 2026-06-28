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

import pathlib
import abc


class ScreenshotMachine(abc.ABC):

    @staticmethod
    def take_screenshot(
        api_key: str,
        url: str,
        image_format: str,
        device: str,
        dimension: str,
        cache_limit: int,
        delay: int
    ) -> str:
        """Return screenshot"""
        return (
            f"Created Screenshot: {api_key}, {url}, {image_format}, {device}, "
            f"{dimension}, {cache_limit}, {delay}"
        )
