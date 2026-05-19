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
PLACEHOLDER_START = "["
PLACEHOLDER_END = "]"


def transform_template_string(template, event):
    """
    Transform string containing template using event data
    :param template: {str} String containing template
    :param event: {dict} Case event
    :return: {str} Transformed string
    """
    index = 0

    while PLACEHOLDER_START in template[index:] and PLACEHOLDER_END in template[index:]:
        partial_template = template[index:]
        start, end = (
            partial_template.find(PLACEHOLDER_START) + len(PLACEHOLDER_START),
            partial_template.find(PLACEHOLDER_END),
        )
        substring = partial_template[start:end]
        value = event.get(substring) if event.get(substring) else ""
        template = template.replace(
            f"{PLACEHOLDER_START}{substring}{PLACEHOLDER_END}", value, 1
        )
        index = index + start + len(value)

    return template
