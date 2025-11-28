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


def _format_style(style_dict: dict) -> str:
    """Converts a dictionary of CSS properties into a style string."""
    return "".join([f"{k}:{v};" for k, v in style_dict.items()])


def card(title: str, content: str, style: dict | None = None) -> str:
    """Generates HTML for a simple card widget.
    
    Args:
        title: The title of the card.
        content: The content of the card.
        style: Optional dictionary of CSS properties for the card container.
    
    Returns:
        A string containing the HTML for the card.
    """

    default_style = {
        "background-color": "#282828",
        "border": "1px solid #444",
        "border-radius": "8px",
        "padding": "16px",
        "margin-bottom": "16px",
        "color": "#e0e0e0",
        "font-family": "Roboto, sans-serif"
    }

    header_style = {
        "font-size": "1.2em",
        "font-weight": "bold",
        "margin-bottom": "8px",
        "color": "#ffffff"
    }

    content_style = {
        "font-size": "1em",
        "line-height": "1.5",
        "color": "#e0e0e0"
    }

    final_style = {**default_style, **(style or {})}

    return f"""
<div style="{_format_style(final_style)}">
    <h3 style="{_format_style(header_style)}">{title}</h3>
    <p style="{_format_style(content_style)}">{content}</p>
</div>
"""
