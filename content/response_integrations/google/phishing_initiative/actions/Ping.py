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

# Imports
from ..core.PhishingInitiativeManager import PhishingInitiativeManager
from soar_sdk.SiemplifyAction import SiemplifyAction

# Consts
DUMMY_URL = "http://www.antiphishing.org/"


@output_handler
def main():
    siemplify = SiemplifyAction()
    # Configuration.
    conf = siemplify.get_configuration("PhishingInitiative")
    api_root = conf["Api Root"]
    api_token = conf["Api Token"]
    phishing_initiative = PhishingInitiativeManager(api_root, api_token)

    res = phishing_initiative.get_url_info(DUMMY_URL)

    if res:
        output_message = "Connection Established."
        result_value = True
    else:
        output_message = "Connection Failed."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
