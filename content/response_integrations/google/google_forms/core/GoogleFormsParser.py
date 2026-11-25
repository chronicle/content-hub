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
from . import datamodels

from TIPCommon.types import SingleJson


class GoogleFormsParser:
    def build_alert_response(
        self,
        raw_data: list[SingleJson],
        form_data: datamodels.FormResponse,
    ) -> list[datamodels.AlertResponse]:
        """Builds a list of AlertResponse objects from JSON data.

        Args:
            raw_data (list[SingleJson]): A list of JSON objects representing
                alert responses.
            form_data (datamodels.FormResponse): The form response data associated
                with the alerts.

        Returns:
            list[datamodels.AlertResponse]: A list of AlertResponse objects constructed
                from the input data.
        """
        return [
            datamodels.AlertResponse.from_json(
                alert_json=alert_json,
                form_json=form_data,
            )
            for alert_json in raw_data
        ]

    def build_form(self, raw_data: SingleJson) -> datamodels.FormResponse:
        """Build an form details object.

        Args:
            raw_data (SingleJson): JSON data for the form from the API response.

        Returns:
            datamodels.Asset: The built form object.
        """
        return datamodels.FormResponse.from_json(raw_data)
