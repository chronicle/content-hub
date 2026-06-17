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

from datetime import datetime

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()

    format = siemplify.extract_action_param("Datetime Format", print_value=True)

    status = EXECUTION_STATE_FAILED
    current_time = "failed"

    try:
        now = datetime.now()
        current_time = now.strftime(format)
        output_message = f"{current_time}"
        status = EXECUTION_STATE_COMPLETED
    except Exception as e:
        siemplify.LOGGER.error(f"Error: {e}")
        output_message = f"ERROR: Failed to get current time - {e}"
    
    siemplify.end(output_message, current_time, status)


if __name__ == "__main__":
    main()
