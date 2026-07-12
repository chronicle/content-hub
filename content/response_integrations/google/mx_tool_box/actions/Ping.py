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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.MXToolBoxManager import MXToolBoxManager

MXTOOLBOX_PROVIDER = "MXToolBox"


@output_handler
def main():
    # Configurations.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(MXTOOLBOX_PROVIDER)
    verify_ssl = conf["Verify SSL"].lower() == "true"
    mx_tool_box_manager = MXToolBoxManager(
        conf["API Root"], conf["API Key"], verify_ssl
    )

    result_value = mx_tool_box_manager.ping()

    if result_value:
        output_message = "Connection Established."
    else:
        output_message = "Connection Failed."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
