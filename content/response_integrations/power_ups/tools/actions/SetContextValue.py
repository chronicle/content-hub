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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

GLOBAL_CONTEXT = 0
IDENTIFIER = "GLOBAL"


def set_global_context(smp, key, value):
    smp.set_context_property(GLOBAL_CONTEXT, IDENTIFIER, key, value)


@output_handler
def main():
    siemplify = SiemplifyAction()

    scope = siemplify.extract_action_param("Scope")
    key = siemplify.extract_action_param("Key")
    value = siemplify.extract_action_param("Value")

    if scope == "Alert":
        siemplify.set_alert_context_property(key, value)
    elif scope == "Case":
        siemplify.set_case_context_property(key, value)
    elif scope == "Global":
        set_global_context(siemplify, key, value)

    output_message = f"Successfully Updated field {key} with value '{value}' in scope {scope}."

    siemplify.end(output_message, True, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
