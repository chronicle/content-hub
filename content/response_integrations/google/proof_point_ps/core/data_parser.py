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

from .data_models import QuarantineRecord


def parse_quarantine_record(data: dict) -> QuarantineRecord:
    """Parse a raw record into QuarantineRecord.

    Args:
        data: The raw JSON dictionary.

    Returns:
        A QuarantineRecord object.

    """
    size_val = data.get("size")
    spamscore_val = data.get("spamscore")
    return QuarantineRecord(
        processingserver=data.get("processingserver"),
        date=data.get("date"),
        subject=data.get("subject"),
        messageid=data.get("messageid"),
        folder=data.get("folder"),
        size=int(size_val) if size_val is not None else None,
        rcpts=data.get("rcpts") or [],
        from_address=data.get("from"),
        spamscore=int(spamscore_val) if spamscore_val is not None else None,
        guid=data.get("guid"),
        host_ip=data.get("host_ip"),
        localguid=data.get("localguid"),
        dlpviolation=data.get("dlpviolation"),
        messagestatus=data.get("messagestatus"),
    )


def parse_quarantine_records(data: dict | list) -> list[QuarantineRecord]:
    """Parse a list of raw records.

    Args:
        data: The raw JSON payload (either a list of records or a dictionary containing 'records' key).

    Returns:
        A list of QuarantineRecord objects.

    """
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = data.get("records") or []
    else:
        records = []
    return [parse_quarantine_record(record) for record in records]
