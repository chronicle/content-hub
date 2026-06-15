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
import re


def get_project_id(projects, project_name):
    """
    Helper function for getting project id from projects list
    :param projects: list of available projects in ASM
    :param project_name: name of project to extact id
    :return: {str} original identifier
    """
    for project in projects:
        if project["name"].lower() == project_name.lower():
            return str(project["id"])

    return None


def sanitize_identifiers(entities_identifier):
    identifiers_sanitized = []

    for identifier in entities_identifier:
        identifier = re.sub("http(s)?:\/\/", "", identifier)
        identifier = re.sub("\/.*", "", identifier)
        identifiers_sanitized.append(identifier)

    return identifiers_sanitized
