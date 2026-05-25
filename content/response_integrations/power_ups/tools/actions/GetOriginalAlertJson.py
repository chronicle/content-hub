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
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ToolsCommon import ExecutionScope

if TYPE_CHECKING:
    from typing import Any


@output_handler
def main():
    try:
        siemplify: SiemplifyAction = SiemplifyAction(get_source_file=True)
    except TypeError:
        siemplify: SiemplifyAction = SiemplifyAction()

    execution_scope: ExecutionScope = getattr(
        siemplify, "execution_scope", ExecutionScope.Alert
    )

    if execution_scope.value == ExecutionScope.Alert.value:
        case_data: Any = json.loads(
            siemplify.current_alert.entities[0]
            .additional_properties["SourceFileContent"],
        )

        siemplify.result.add_result_json([case_data])
        siemplify.end("See technical details", json.dumps([case_data]))

    else:
        combined_results: list = []
        case_alerts = getattr(siemplify.case, "open_alerts", siemplify.case.alerts)
        for alert in case_alerts:
            try:
                if alert.entities:
                    case_data: Any = json.loads(
                        alert.entities[0].additional_properties["SourceFileContent"],
                    )
                    combined_results.append(case_data)
            except (KeyError, IndexError) as e:
                siemplify.LOGGER.error(
                    f"Error extracting SourceFileContent for alert {alert.identifier}:"
                    f" {e}"
                )
                
        siemplify.result.add_result_json(combined_results)
        siemplify.end("See technical details", json.dumps(combined_results))


if __name__ == "__main__":
    main()
