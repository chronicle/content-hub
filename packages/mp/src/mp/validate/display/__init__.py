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

from mp.core.display_utils import DisplayReport, display_reports
from mp.core.utils import is_github_actions

from .cli import CliDisplay
from .html.html import HtmlFormat
from .markdown_format import MarkdownFormat

if TYPE_CHECKING:
    from mp.validate.data_models import ContentType, FullReport


def display_validation_reports(validation_results: dict[ContentType, FullReport]) -> None:
    """Display validation results for multiple content types.

    Args:
        validation_results: A dictionary where keys are ContentType enums (INTEGRATION, PLAYBOOK)
        and values are the FullReport (dict of stages) for that type.

    """
    display_types_list: list[DisplayReport] = [CliDisplay(validation_results)]

    if is_github_actions():
        display_types_list.append(MarkdownFormat(validation_results))
    else:
        display_types_list.append(HtmlFormat(validation_results))

    display_reports(*display_types_list)
