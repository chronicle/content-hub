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

from typing import NoReturn

import collections
import requests

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string, string_to_multi_value
from TIPCommon.validation import ParameterValidator
from ..core import api_utils
from ..core import constants
from ..core import datamodels
from ..core import exceptions
from ..core import AuthenticationManager as auth_manager
from ..core import PaloAltoPrismaCloudManager as api_manager


EnrichAssetsResult = collections.namedtuple(
    "EnrichAssetsResult", ["valid_enrich_assets", "invalid_enrich_assets"]
)


class EnrichAssetsAction(Action):

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action "{constants.ENRICH_ASSETS_SCRIPT_NAME}".'
        )
        self.json_results = {}
        self.result_value = True

    def _extract_parameters(self) -> None:
        integration_params = api_utils.get_integration_params(self.soar_action)
        self.params.session_auth_params = integration_params.auth_params
        self.params.api_params = integration_params.api_params

        self.params.asset_identifiers = extract_action_param(
            self.soar_action,
            param_name="Asset Identifiers",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        ParameterValidator.validate_csv(
            self,
            param_name="Asset Identifiers",
            csv_string=self.params.asset_identifiers,
        )

    def _init_managers(self) -> api_manager.ApiManager:
        session = self._get_authenticated_session()
        return api_manager.ApiManager(
            session=session,
            api_parameters=self.params.api_params,
            logger=self.soar_action.LOGGER,
        )

    def _get_authenticated_session(self) -> requests.Session:
        return auth_manager.get_authenticated_session(self.params.session_auth_params)

    def _enrich_assets(self, manager: api_manager.ApiManager, enrich_assets: list[str]):
        """Retrieve enrich assets information for a given asset_id.

        Args:
            manager (ApiManager): The ApiManager instance.
            enrich_assets (list[str]): A list of enrich_assets to retrieve information
                from.
        """
        valid_enrich_assets = []
        invalid_enrich_assets = []

        for asset in enrich_assets:
            try:
                enrich_assets = manager.enrich_assets(asset=asset)
                valid_enrich_assets.append(enrich_assets.raw_data)

            except exceptions.PaloAltoPrismaCloudError:
                invalid_enrich_assets.append(asset)

        return EnrichAssetsResult(valid_enrich_assets, invalid_enrich_assets)

    def _perform_action(self, manager: api_manager.ApiManager, _=None) -> None:
        self.logger.info("Successfully connected to Palo Alto Prisma Cloud")
        self.params.asset_identifiers = string_to_multi_value(
            self.params.asset_identifiers
        )
        self.logger.info("Enriching assets with provided identifiers")
        assets = self._enrich_assets(
            manager=manager, enrich_assets=self.params.asset_identifiers
        )
        self.logger.info("Setting action result with enriched assets")
        self._set_action_result(
            assets.valid_enrich_assets, assets.invalid_enrich_assets
        )

    def _set_action_result(
        self, valid_assets: datamodels.Asset, invalid_assets: datamodels.Asset
    ) -> None:
        asset_ids = [asset["id"] for asset in valid_assets]
        valid_assets_ids = convert_list_to_comma_string(asset_ids)
        invalid_assets_ids = convert_list_to_comma_string(invalid_assets)
        self.json_results = valid_assets
        if valid_assets:
            self.output_message = (
                f"Successfully enriched the following resources using information from "
                f"{constants.INTEGRATION_DISPLAY_NAME}: {valid_assets_ids}\n"
            )
        else:
            self.result_value = True
            self.output_message = "None of the provided assets were enriched."

        if invalid_assets and valid_assets:
            self.output_message += (
                f"Action wasn’t able to enrich the following assets using "
                f"information from  {constants.INTEGRATION_DISPLAY_NAME}: "
                f"{invalid_assets_ids}"
            )


def main() -> NoReturn:
    action = EnrichAssetsAction(constants.ENRICH_ASSETS_SCRIPT_NAME)
    action.run()


if __name__ == "__main__":
    main()
