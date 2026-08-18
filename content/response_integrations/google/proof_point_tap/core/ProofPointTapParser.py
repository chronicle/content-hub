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
from TIPCommon.types import SingleJson
from ..core import constants
from ..core import datamodels


def build_results(
    raw_json, method, data_key="data", pure_data=False, limit=None, **kwargs
):
    return [
        method(item_json, **kwargs)
        for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[:limit]
    ]


def build_forensic_data_object(raw_data, filters, limit=None):
    """
    Builds a ForensicObj data model from raw API response.

    Args:
        raw_data (dict): The raw JSON response from the API.
        filters (list): A list of forensic types to filter the results by.
        limit (int, optional): The maximum number of forensics to return.

    Returns:
        datamodels.ForensicObj: A ForensicObj data model containing the processed
        forensic data.
    """
    raw_data = raw_data.get("reports", [])[0] if raw_data.get("reports", []) else []
    if filters:
        filtered_data = _filter_results_by_type(raw_data.get("forensics", []), filters)
        raw_data.update({"forensics": filtered_data[:limit]})

    return datamodels.ForensicObj(
        raw_data=raw_data,
        forensics=(
            build_results(
                raw_data.get("forensics"),
                method=build_forensic_obj,
                pure_data=True,
            )
            if raw_data.get("forensics")
            else []
        ),
    )


def _filter_results_by_type(data, filters):
    results = []
    for item in data:
        if item.get("type", "") in filters:
            results.append(item)

    return results


def build_campaign_obj(raw_data):
    return datamodels.Campaign(raw_data=raw_data, **raw_data)


def build_forensic_obj(raw_data):
    return datamodels.Forensic(raw_data=raw_data, **raw_data)


def build_decode_url(raw_data):
    return datamodels.DecodedURL(raw_data=raw_data, **raw_data)


def build_events_results(raw_data: SingleJson, event_type: str):
    """
    Builds a list of Event objects from the raw data.
    Args:
        raw_data (SingleJson): The raw JSON data containing the events.
        event_type (str): The type of the event.
    Returns:
        list[datamodels.Event]: A list of Event objects.
    """
    results = []
    for event_subtype in constants.EVENT_TYPE_MAPPING.get(event_type, []):
        results.extend(
            [
                build_event_obj(event_data, event_subtype)
                for event_data in raw_data.get(event_subtype, [])
            ]
        )

    return results


def build_event_obj(
    raw_data: SingleJson,
    event_type: str,
) -> datamodels.Event:
    """
    Builds an Event object from the raw data.
    Args:
        raw_data (SingleJson): The raw JSON data of the event.
        event_type (str): The type of the event.
    Returns:
        datamodels.Event: The Event object.
    """
    return datamodels.Event.from_json(event_data=raw_data, event_type=event_type)


def build_campaigns_results(raw_data: SingleJson):
    """Builds a list of Campaign objects from the raw data.

    Args:
        raw_data (SingleJson): The raw JSON data containing the campaigns.

    Returns:
        list[datamodels.Campaign]: A list of Campaign objects.
    """
    return [
        build_campaign_obj(campaign_data)
        for campaign_data in raw_data.get("campaigns", [])
    ]


def build_threat_report(
    report_data: SingleJson,
    max_results: int,
) -> datamodels.ThreatReport:
    """
    Builds a ThreatReport object from raw report data and limits the
    number of forensics.

    Args:
        report_data (SingleJson): Raw JSON of a single report.
        max_results (int): Max number of forensics to include.

    Returns:
        ThreatReport: Structured ThreatReport object.
    """
    forensics_raw = report_data.get("forensics", [])[:max_results]
    forensics = [build_threat_forensic(f_data) for f_data in forensics_raw]

    return datamodels.ThreatReport.from_json(
        {
            "scope": report_data.get("scope"),
            "id": report_data.get("id"),
            "name": report_data.get("name"),
            "threatStatus": report_data.get("threatStatus"),
            "forensics": [f.to_json() for f in forensics],
        }
    )


def build_threat_forensic(data: SingleJson) -> datamodels.ThreatForensic:
    return datamodels.ThreatForensic.from_json(data)
