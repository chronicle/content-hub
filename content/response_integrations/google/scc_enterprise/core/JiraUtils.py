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

from typing import Any


def extract_text_from_adf(content: Any) -> str:
    """Extracts plain text from an Atlassian Document Format (ADF) structure.

    This function recursively navigates through a nested structure of dictionaries
    and lists that represent a document in Atlassian's standard format for
    rich text. It extracts and concatenates the text from various node types.

    Args:
        content (Any): The ADF content, which can be a dictionary representing a
            node, a list of nodes, or a simple string.

    Returns:
        str: The extracted plain text content from the ADF structure.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        if content.get("type") == "text":
            return str(content.get("text", ""))

        node_type: str = str(content.get("type", ""))
        extracted: str = ""

        if "content" in content:
            parts: list[str] = [
                extract_text_from_adf(item) for item in content["content"]
            ]
            extracted = "".join(parts)

        if node_type == "paragraph":
            return extracted + "\n"

        return extracted

    if isinstance(content, list):
        list_parts: list[str] = [extract_text_from_adf(item) for item in content]
        return "".join(list_parts)

    return str(content) if content is not None else ""
