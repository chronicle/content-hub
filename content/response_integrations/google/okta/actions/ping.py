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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.OktaManager import OktaManager, OktaException


PROVIDER = "Okta"


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(PROVIDER)
    api_root = conf.get("Api Root")
    api_token = conf.get("Api Token")
    client_id = conf.get("Client ID")
    use_oauth_authentication = (
        str(conf.get("Use Oauth Authentication", "false")).lower() == "true"
    )
    key_id = conf.get("Key ID")
    private_key = conf.get("Private Key")
    verify_ssl = str(conf.get("Verify SSL", "false")).lower() == "true"

    try:
        okta = OktaManager(
            api_root=api_root,
            api_token=api_token,
            client_id=client_id,
            use_oauth_authentication=use_oauth_authentication,
            key_id=key_id,
            private_key=private_key,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )
        okta.test_connectivity()
        output_message = "Connection Established Successfully"
        result = True
        status = EXECUTION_STATE_COMPLETED
    except OktaException as err:
        output_message = f"Connection Failed: {err}"
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
