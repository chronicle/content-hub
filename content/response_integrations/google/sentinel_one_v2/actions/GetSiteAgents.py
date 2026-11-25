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

from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.validation import ParameterValidator

from ..core.constants import (
    GET_SITE_AGENTS_SCRIPT_NAME,
    INTEGRATION_NAME,
    MAX_AGENTS_TO_RETURN,
    MIN_AGENTS_TO_RETURN,
)
from ..core.exceptions import SiteNameNotFoundError
from ..core.SentinelOneV2Factory import SentinelOneV2ManagerFactory

if TYPE_CHECKING:
    from typing import NoReturn, List

    from ..core.SentinelOneV2ManagerV2 import SentinelOneV2ManagerV2

    from TIPCommon.types import SingleJson


class GetSiteAgents(Action):

    def __init__(self) -> None:
        super().__init__(GET_SITE_AGENTS_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Api Root",
            is_mandatory=True,
            print_value=True,
        )
        self.params.api_token = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Token",
            is_mandatory=True,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            default_value=False,
            input_type=bool,
        )
        self.params.site_name = extract_action_param(
            self.soar_action,
            param_name="Site Name",
            is_mandatory=True,
            print_value=True,
        )
        self.params.limit = extract_action_param(
            self.soar_action,
            param_name="Max Agents To Return",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        self.params.limit = validator.validate_range(
            param_name="Max Agents To Return",
            value=self.params.limit,
            min_limit=MIN_AGENTS_TO_RETURN,
            max_limit=MAX_AGENTS_TO_RETURN,
        )

    def _init_api_clients(self) -> SentinelOneV2ManagerV2:
        return SentinelOneV2ManagerFactory().get_manager(
            api_root=self.params.api_root,
            api_token=self.params.api_token,
            verify_ssl=self.params.verify_ssl,
            force_check_connectivity=True,
            logger=self.logger,
        )

    def _perform_action(self, _) -> None:
        sites_data: SingleJson = self.api_client.get_site_by_name(site_name=self.params.site_name)
        sites: List[SingleJson] = sites_data.get("data", {}).get(
            "sites", []
        )

        if not sites:
            error_output_message: str = (
                f'Site "{self.params.site_name}" not found in SentinelOne. Please check the spelling.'
            )
            raise SiteNameNotFoundError(error_output_message)

        site_ids = [site.get("id") for site in sites if site.get("id")]
        all_agents = self.api_client.get_agents_by_site(
            site_ids=",".join(site_ids),
            limit=self.params.limit,
        )

        if all_agents:
            self.json_results = [agent.to_json() for agent in all_agents]
            self.output_message = (
                "Successfully returned information about the hosts from Site "
                f"{self.params.site_name} in SentinelOne"
            )
        else:
            self.output_message = (
                f"No hosts are associated with Site {self.params.site_name} "
                "in SentinelOne"
            )


def main() -> NoReturn:
    GetSiteAgents().run()


if __name__ == "__main__":
    main()
