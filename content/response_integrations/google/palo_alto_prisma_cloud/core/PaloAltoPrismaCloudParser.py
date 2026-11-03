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


def build_alert_response(raw_data: list[SingleJson]) -> list[datamodels.AlertResponse]:
    """Build a list of alert response object from JSON data.

    Args:
        raw_data (SingleJson): The JSON data representing alert_response.

    Returns:
        list[datamodels.AlertResponse]: A list of alert Response objects.
    """
    return [
        datamodels.AlertResponse.from_json(alert_json=alert_json)
        for alert_json in raw_data
    ]


def build_asset(raw_data: SingleJson) -> datamodels.Asset:
    """Build an Asset object.

    Args:
        raw_data (SingleJson): JSON data for the asset from the API response.

    Returns:
        datamodels.Asset: The built Asset object.
    """
    return datamodels.Asset.from_json(raw_data)


def build_alert(raw_data: SingleJson) -> datamodels.Alert:
    """Build an Asset object.

    Args:
        raw_data (SingleJson): JSON data for the asset from the API response.

    Returns:
        datamodels.Asset: The built Asset object.
    """
    return datamodels.Alert.from_json(raw_data)
