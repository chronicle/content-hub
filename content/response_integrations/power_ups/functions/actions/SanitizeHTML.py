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

import bleach
from bleach.css_sanitizer import CSSSanitizer
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


def allow_attrs(tag, name, value):
    return True


@output_handler
def main():
    siemplify = SiemplifyAction()
    tags = list(
        filter(
            None,
            [x.strip() for x in siemplify.extract_action_param("Tags", " ").split(",")],
        ),
    )
    attributes = list(
        filter(
            None,
            [
                x.strip()
                for x in siemplify.extract_action_param("Attributes", " ").split(",")
            ],
        ),
    )
    styles = list(
        filter(
            None,
            [
                x.strip()
                for x in siemplify.extract_action_param("Styles", " ").split(",")
            ],
        ),
    )
    css_sanitizer = CSSSanitizer(allowed_css_properties=styles)
    input = siemplify.parameters.get("Input HTML")
    (
        str(
            siemplify.extract_action_param(
                param_name="Allow All Tags",
                is_mandatory=False,
                print_value=False,
                default_value="false",
            ),
        ).lower()
        == "true"
    )
    allow_all_attrs = (
        str(
            siemplify.extract_action_param(
                param_name="Allow All Attributes",
                is_mandatory=False,
                print_value=False,
                default_value="false",
            ),
        ).lower()
        == "true"
    )
    (
        str(
            siemplify.extract_action_param(
                param_name="Allow All Styles",
                is_mandatory=False,
                print_value=False,
                default_value="false",
            ),
        ).lower()
        == "true"
    )

    if tags and styles and attributes:
        sanatized = bleach.clean(
            input,
            tags=tags,
            css_sanitizer=css_sanitizer,
            attributes=attributes,
        )
    elif tags and styles and allow_all_attrs:
        sanatized = bleach.clean(
            input,
            tags=tags,
            css_sanitizer=css_sanitizer,
            attributes=allow_attrs,
        )
    elif tags and attributes and not styles:
        sanatized = bleach.clean(input, tags=tags, attributes=attributes)
    elif tags and allow_all_attrs and not styles:
        sanatized = bleach.clean(input, tags=tags, attributes=allow_attrs)
    elif tags and not styles and not attributes:
        sanatized = bleach.clean(input, tags=tags)
    elif styles and attributes and not tags:
        sanatized = bleach.clean(
            input,
            css_sanitizer=css_sanitizer,
            attributes=attributes,
        )
    elif styles and allow_all_attrs and tags:
        sanatized = bleach.clean(
            input,
            css_sanitizer=css_sanitizer,
            attributes=allow_attrs,
        )
    elif styles and not tags and not attributes and not allow_all_attrs:
        sanatized = bleach.clean(input, css_sanitizer=css_sanitizer)
    elif attributes and tags and not styles:
        sanatized = bleach.clean(input, tags=tags, attributes=attributes)
    elif attributes and styles and not tags and not allow_all_attrs:
        sanatized = bleach.clean(
            input,
            attributes=attributes,
            css_sanitizer=css_sanitizer,
        )
    elif attributes and not styles and not tags and not allow_all_attrs:
        sanatized = bleach.clean(input, attributes=attributes)
    elif allow_all_attrs and not tags and not styles:
        sanatized = bleach.clean(input, attributes=allow_attrs)
    else:
        sanatized = bleach.clean(input)
    result = sanatized
    output_message = f"{input} successfully sanitized to: {result}"
    siemplify.end(output_message, result, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
