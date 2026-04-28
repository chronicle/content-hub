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

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


def get_list_param(smp, param_name):
    param = smp.extract_action_param(param_name, " ")
    try:
        return set(json.loads(param))
    except:
        # Split by comma, Strip or convert to Int, filter None and empty strings, return set
        return set(
            filter(
                lambda v: v is not None and v != "",
                [x.strip() if not x.isdigit() else int(x) for x in param.split(",")],
            ),
        )


@output_handler
def main():
    siemplify = SiemplifyAction()
    original = get_list_param(siemplify, "Original")
    subset = get_list_param(siemplify, "Subset")

    result_value = subset <= original

    if result_value:
        output_message = "All items from the subset list are in the original list"
    else:
        output_message = (
            f"Found items which are not in the original list: {','.join(sorted(str(x) for x in subset - original))}"
        )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
