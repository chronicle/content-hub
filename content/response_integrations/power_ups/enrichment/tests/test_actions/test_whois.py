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

from unittest.mock import MagicMock, patch

import pytest
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import Whois
from ..core.product import EnrichmentProduct
from ..core.session import EnrichmentMockSession

MOCK_GOOGLE_RDAP = {
    "objectClassName": "domain",
    "handle": "2138514_DOMAIN_COM-VRSN",
    "ldhName": "GOOGLE.COM",
    "events": [
        {"eventAction": "registration", "eventDate": "1997-09-15T04:00:00Z"},
        {"eventAction": "expiration", "eventDate": "2028-09-14T04:00:00Z"},
        {"eventAction": "last changed", "eventDate": "2019-09-09T15:39:04Z"}
    ],
    "entities": [
        {
            "roles": ["registrar"],
            "vcardArray": ["vcard", [["version", {}, "text", "4.0"], ["fn", {}, "text", "MarkMonitor Inc."]]]
        }
    ]
}

MOCK_AFNIC_RDAP = {
    "objectClassName": "domain",
    "ldhName": "univ-lyon1.fr",
    "events": [
        {"eventAction": "registration", "eventDate": "1994-12-31T23:00:00Z"},
        {"eventAction": "expiration", "eventDate": "2026-12-31T23:00:00Z"}
    ],
    "entities": [
        {
            "handle": "ULUC6-FRNIC",
            "roles": ["registrant"],
            "vcardArray": [
                "vcard",
                [
                    ["version", {}, "text", "4.0"],
                    ["fn", {}, "text", "UNIVERSITE LYON 1 CLAUDE BERNARD"],
                    [
                        "adr",
                        {"cc": "FR"},
                        "text",
                        ["", "", "43, boulevard du 11 Novembre 1918", "Villeurbanne", "", "69622"],
                    ],
                ],
            ]
        },
        {
            "handle": "FF16254-FRNIC",
            "roles": ["administrative"],
            "vcardArray": ["vcard", [["version", {}, "text", "4.0"], ["fn", {}, "text", "Frédéric Fleury"]]]
        },
        {
            "handle": "CG47488-FRNIC",
            "roles": ["technical"],
            "vcardArray": ["vcard", [["version", {}, "text", "4.0"], ["fn", {}, "text", "Cédric Gallo"]]]
        }
    ]
}

MOCK_GOOGLE_WHOIS = """Domain Name: GOOGLE.COM
Registrar: MarkMonitor Inc.
Creation Date: 1997-09-15T04:00:00Z
"""


@pytest.fixture(autouse=True)
def setup_whois_action_mocks(
    monkeypatch: pytest.MonkeyPatch,
    mock_siemplify: MagicMock,
) -> None:
    monkeypatch.setattr(
        Whois,
        "SiemplifyAction",
        lambda: mock_siemplify,
    )

    def mock_extract(url, *args, **kwargs):
        mock_res = MagicMock()
        if "univ-lyon1.fr" in url:
            mock_res.registered_domain = "univ-lyon1.fr"
        else:
            mock_res.registered_domain = "google.com"
        return mock_res

    monkeypatch.setattr(
        Whois,
        "extract",
        mock_extract,
    )


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters={"Create Entities": "true", "Domain Age Threshold": "0"},
    input_context={"environment": "Default", "alert_id": "alert_1"},
)
def test_whois_action_standard_domain_rdap(
    product: EnrichmentProduct,
    script_session: EnrichmentMockSession,
    action_output: MockActionOutput,
    mock_siemplify: MagicMock,
) -> None:
    product.set_case_metadata({"title": "Simulated Whois Case", "case_id": "case_whois"})
    product.set_alerts_full_details({
        "alerts": [
            {
                "identifier": "alert_1",
                "entities": [
                    {
                        "identifier": "google.com",
                        "entity_type": "DOMAIN",
                        "additional_properties": {},
                    }
                ],
            }
        ]
    })

    # Mock requests.get to return MOCK_GOOGLE_RDAP
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_GOOGLE_RDAP
        mock_get.return_value = mock_response

        Whois.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    
    res_list = mock_siemplify.result.add_result_json.call_args[0][0]
    assert len(res_list) == 1
    assert res_list[0]["Entity"] == "google.com"
    assert res_list[0]["EntityResult"]["registrar"][0] == "MarkMonitor Inc."
    assert res_list[0]["EntityResult"]["id"] == ["2138514_DOMAIN_COM-VRSN"]
    assert "raw" in res_list[0]["EntityResult"]
    assert isinstance(res_list[0]["EntityResult"]["raw"], list)
    assert len(res_list[0]["EntityResult"]["raw"]) == 1


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters={"Create Entities": "true", "Domain Age Threshold": "0"},
    input_context={"environment": "Default", "alert_id": "alert_1"},
)
def test_whois_action_afnic_domain_rdap(
    product: EnrichmentProduct,
    script_session: EnrichmentMockSession,
    action_output: MockActionOutput,
    mock_siemplify: MagicMock,
) -> None:
    product.set_case_metadata({"title": "Simulated Whois Case", "case_id": "case_whois"})
    product.set_alerts_full_details({
        "alerts": [
            {
                "identifier": "alert_1",
                "entities": [
                    {
                        "identifier": "univ-lyon1.fr",
                        "entity_type": "DOMAIN",
                        "additional_properties": {},
                    }
                ],
            }
        ]
    })

    # Mock requests.get to return MOCK_AFNIC_RDAP
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_AFNIC_RDAP
        mock_get.return_value = mock_response

        Whois.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    
    res_list = mock_siemplify.result.add_result_json.call_args[0][0]
    assert len(res_list) == 1
    assert res_list[0]["Entity"] == "univ-lyon1.fr"
    assert res_list[0]["EntityResult"]["id"] == ["univ-lyon1.fr"]
    contacts = res_list[0]["EntityResult"]["contacts"]
    
    assert contacts["registrant"]["handle"] == "ULUC6-FRNIC"
    assert contacts["registrant"]["name"] == "UNIVERSITE LYON 1 CLAUDE BERNARD"
    assert contacts["admin"]["handle"] == "FF16254-FRNIC"
    assert contacts["tech"]["handle"] == "CG47488-FRNIC"


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters={"Create Entities": "true", "Domain Age Threshold": "0"},
    input_context={"environment": "Default", "alert_id": "alert_1"},
)
def test_whois_action_fallback_to_classic_whois(
    product: EnrichmentProduct,
    script_session: EnrichmentMockSession,
    action_output: MockActionOutput,
    mock_siemplify: MagicMock,
) -> None:
    product.set_case_metadata({"title": "Simulated Whois Case", "case_id": "case_whois"})
    product.set_alerts_full_details({
        "alerts": [
            {
                "identifier": "alert_1",
                "entities": [
                    {
                        "identifier": "google.com",
                        "entity_type": "DOMAIN",
                        "additional_properties": {},
                    }
                ],
            }
        ]
    })

    # Mock requests.get to fail (e.g. 500 status)
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Mock whois network request to return standard mock data
        with patch("whois_alt.net.whois_request") as mock_req:
            def whois_request_side_effect(domain, server, *args, **kwargs):
                if server == "whois.iana.org":
                    return "refer: whois.verisign-grs.com\n"
                elif server == "whois.verisign-grs.com":
                    return MOCK_GOOGLE_WHOIS
                return ""
            mock_req.side_effect = whois_request_side_effect

            Whois.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    
    res_list = mock_siemplify.result.add_result_json.call_args[0][0]
    assert len(res_list) == 1
    assert res_list[0]["Entity"] == "google.com"
    assert res_list[0]["EntityResult"]["registrar"][0] == "MarkMonitor Inc."
    assert "raw" in res_list[0]["EntityResult"]
    assert isinstance(res_list[0]["EntityResult"]["raw"], list)
