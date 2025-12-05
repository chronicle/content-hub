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

import re
from typing import TYPE_CHECKING, NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param

from ..core.constants import DEFANG_TEXT_SCRIPT_NAME

if TYPE_CHECKING:
    from typing import Any


class DefangTextAction(Action):
    """Action to defang text by modifying URLs, IPs, and emails."""

    def __init__(self) -> None:
        super().__init__(DEFANG_TEXT_SCRIPT_NAME)
        self.output_message: str = "Successfully defanged the input."

    def _init_api_clients(self) -> None:
        """Initialize API clients if required (placeholder)."""

    def _extract_action_parameters(self) -> None:
        """Extracts all action parameters."""
        self.params.input_text = extract_action_param(
            self.soar_action,
            "Input",
            print_value=True,
        )

    def _perform_action(self, _: Any = None) -> None:
        if not self.params.input_text:
            self.output_message = "Input text is empty."
            self.json_results = {"converted_text": ""}
            return

        # Defang HTTP/HTTPS
        defanged_text = re.sub(
            r"https?://([a-zA-Z0-9.-]+)",
            lambda m: m.group(0)
            .replace("http", "hxxp")
            .replace(m.group(1), m.group(1).replace(".", "[.]")),
            self.params.input_text,
        )

        # Defang IPs (e.g., 1.1.1.1 -> 1[.]1[.]1[.]1)
        # Simple regex for IPv4
        defanged_text = re.sub(
            r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})",
            r"\1[.]\2[.]\3[.]\4",
            defanged_text,
        )

        # Defang Emails (e.g., user@example.com -> user[at]example[.]com)
        defanged_text = re.sub(
            r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            lambda m: m.group(1) + "[at]" + m.group(2).replace(".", "[.]"),
            defanged_text,
        )

        self.json_results = {"converted_text": defanged_text}


def main() -> NoReturn:
    DefangTextAction().run()


if __name__ == "__main__":
    main()
