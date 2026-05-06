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

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_email_template

HTML_TYPES = {1, "HtmlFormat"}
STANDARD_TYPES = {0, "Template"}


def is_html_template(template_type: str, template_type_value: str | int) -> bool:
    """Check if the template is of HTML type."""
    return template_type == "HTML" and template_type_value in HTML_TYPES


def is_standard_template(template_type: str, template_type_value: str | int) -> bool:
    """Check if the template is of Standard type."""
    return template_type == "Standard" and template_type_value in STANDARD_TYPES


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.SCRIPT_NAME = "Get Email Templates"

    template_type = siemplify.extract_action_param("Template Type", print_value=True)

    status = EXECUTION_STATE_COMPLETED
    output_message = "output message :"  # human readable message, showed in UI as the action result

    email_templates = get_email_template(siemplify)
    res = []

    for template in email_templates:
        template_json = template.to_json()
        template_type_value = template_json.get("type")

        if is_html_template(template_type, template_type_value) or is_standard_template(
            template_type, template_type_value
        ):
            res.append(template_json)

    siemplify.result.add_result_json({"templates": res})
    siemplify.end(output_message, json.dumps(res), status)


if __name__ == "__main__":
    main()
