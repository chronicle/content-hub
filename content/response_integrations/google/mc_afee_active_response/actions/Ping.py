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

from ..core.McAfeeActiveResponseManager import McAfeeActiveResponseManager

PROVIDER = "McAfeeActiveResponse"


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(PROVIDER)

    try:
        # The connection is established at the Init function of the class.
        McAfeeActiveResponseManager(
            conf.get("Broker URLs List").split(",") if conf.get("Broker URLs List") else [],
            conf.get("Broker CA Bundle File Path"),
            conf.get("Certificate File Path"),
            conf.get("Private Key File Path"),
        )
        siemplify.end("Successfully connected to the McAfee Active Response server.", True)
    except Exception as e:
        siemplify.logger.exception(f"Failed to connect to the McAfee Active Response server. Error: {e}")
        siemplify.end("Failed to connect to the McAfee Active Response server.", False)


if __name__ == "__main__":
    main()
