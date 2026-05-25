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
from ..core.PassiveTotalManager import PassiveTotal


@output_handler
def main():
    siemplify = SiemplifyAction()
    configuration = siemplify.get_configuration("PassiveTotal")
    passive_total = PassiveTotal(
        user=configuration["Username"], key=configuration["Api_Key"]
    )

    whois_dict = passive_total.get_whois_report("google.com")

    # In case of error
    if whois_dict.get("message"):
        # Print Error
        print(whois_dict.get("message"))
        whois_dict = None

    output_message = "Connection Established" if whois_dict else "Connection Failed"
    result_value = True if whois_dict else False
    siemplify.end(output_message, result_value)

if __name__ == "__main__":
    main()
