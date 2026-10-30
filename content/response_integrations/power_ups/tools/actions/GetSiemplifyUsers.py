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

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_siemplify_user_details

ACTION_NAME = "GetSiemplifyUsers"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    hide_disabled = siemplify.parameters.get("Hide Disabled Users").lower() == "true"
    siemplify_users = get_siemplify_user_details(
        chronicle_soar=siemplify,
        search_term="",
        filter_by_role=False,
        requested_page=0,
        page_size=1000,
        should_hide_disabled_users=hide_disabled,
    )
    siemplify.result.add_result_json(
        {"siemplifyUsers": [s_user.to_json() for s_user in siemplify_users]},
    )
    output_message = "Returned Siemplify Users."
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
