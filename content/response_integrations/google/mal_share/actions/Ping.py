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
from ..core.MalShareManager import MalShareManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    # Configuration.
    conf = siemplify.get_configuration("MalShare")
    api_key = conf["Api Key"]
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    malshare = MalShareManager(api_key, verify_ssl)

    malshare.test_connectivity()

    # If no exception occur - then connection is successful
    siemplify.end("Connected successfully.", "true")


if __name__ == "__main__":
    main()
