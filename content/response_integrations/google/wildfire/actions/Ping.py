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

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.WildfireManager import WildfireManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Wildfire")
    api_key = conf["Api Key"]

    # Connect to Wildfire
    wildfire_manager = WildfireManager(api_key)

    # Test connectivity
    connectivity = wildfire_manager.test_connectivity()

    # If no exception occurs - then connection is successful
    if connectivity:
        output_message = "Successfully connected to the Wildfire."
    else:
        output_message = "Failed to connect to the Wildfire."
    siemplify.end(output_message, connectivity)


if __name__ == "__main__":
    main()
