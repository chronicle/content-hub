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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.CertlyManager import CertlyManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    try:
        conf = siemplify.get_configuration("Certly")
        api_token = conf["Api Token"]
        api_url = conf["Api Root"]
        verify_ssl = conf.get("Verify SSL", "true").lower() == "true"
        certly = CertlyManager(api_token, api_url, verify_ssl=verify_ssl)
        certly.test_connectivity()
        output_message = "Successfully connected to the Certly server with the provided connection parameters!"
        result_value = True
        status = EXECUTION_STATE_COMPLETED
    except Exception as err:
        output_message = f"Failed to connect to the Certly server! Error is {err}"
        result_value = False
        status = EXECUTION_STATE_FAILED
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
