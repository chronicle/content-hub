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

"""Mock and sample alert data for FireEye ETP unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

SAMPLE_V2_ALERT: SingleJson = {
    "id": "c13ef31b-7a71-4770-b74a-4e2b0244ba07",
    "domain": "customer.com",
    "verdict": "malicious",
    "alert": {
        "name": "malware-object",
        "severity": "majr",
        "occurred": "2026-08-20T02:54:32.000000",
        "email-header": {
            "from": '"Sender Name" <sender@test.com>',
            "to": "recipient@customer.com",
            "subject": "Payment Details",
            "message-id": "<msg-001@test.com>",
        },
        "smtp-message": {
            "from": "sender@test.com",
            "to": ["recipient@customer.com"],
            "ip_address": "192.0.2.1",
            "threat_type": "malware",
            "sender_domain": "test.com",
        },
        "explanation": {
            "malware-detected": {
                "malware": [
                    {
                        "name": "Trojan.Generic",
                        "md5sum": "d41d8cd98f00b204e9800998ecf8427e",
                        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                        "original": "invoice.pdf",
                    }
                ]
            }
        },
    },
}

SAMPLE_SEARCH_ALERT: SingleJson = {
    "id": "search-alert-002",
    "report_id": "search-alert-002",
    "accepted_time": "20260820025319",
    "alert_date": "2026-08-20T02:53:19.000Z",
    "severity": "crit",
    "mta_msg_id": "<mta-12345@evil.com>",
    "malware": [
        {
            "name": "Exploit.CVE",
            "md5": "d41d8cd98f00b204e9800998ecf8427e",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "original": "exploit.doc",
        }
    ],
    "smtp-message": {
        "to": ["user1@customer.com", "user2@customer.com"],
        "from": "attacker@evil.com",
        "ip_address": "198.51.100.1",
    },
    "email-header": {
        "from": "attacker@evil.com",
        "to": "user1@customer.com",
        "subject": "Urgent Security Notice",
        "message-id": "<mta-12345@evil.com>",
    },
}

SAMPLE_ALERTS: list[SingleJson] = [
    SAMPLE_V2_ALERT,
    SAMPLE_SEARCH_ALERT,
]

MOCK_V2_ROOT_DETAIL_RESPONSE: SingleJson = {
    "id": "alert-123",
    "alert": {
        "name": "malware-object",
        "severity": "majr",
        "occurred": "2026-08-20T02:54:32.000000",
        "email-header": {"message-id": "<msg123>", "subject": "Test"},
        "smtp-message": {"from": "sender@test.com", "to": ["rcpt@test.com"]},
        "explanation": {
            "malware-detected": {
                "malware": [{"name": "TestMalware", "md5sum": "12345", "sha256": "67890"}]
            }
        },
    },
}

MOCK_V2_WRAPPED_DETAIL_RESPONSE: SingleJson = {
    "data": {
        "id": "alert-456",
        "alert": {
            "severity": "crit",
            "occurred": "2026-08-20T02:54:32.000000",
            "email-header": {"message-id": "<msg456>"},
        },
    }
}
