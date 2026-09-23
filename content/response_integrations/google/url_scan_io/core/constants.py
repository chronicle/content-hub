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
INTEGRATION_NAME = "UrlScanIo"

# ACTION NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Ping'}"
GET_SCAN_FULL_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Get Scan Full Details'}"
URL_CHECK_ACTION_NAME = f"{INTEGRATION_NAME} - {'Url Check'}"
SEARCH_FOR_SCANS_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Search For Scans'}"

# DEFAULTS
DEFAULT_COUNTS = 100
DEFAULT_THRESHOLD = 0

# CASE WALL CONSTANTS
CASE_WALL_LINK = "https://urlscan.io/result/{}"
WEB_REPORT_LINK_TITLE = "{} Web Report - {}"
DOM_TREE_LINK_TITLE = "{} DOM Tree - {}"
ATTACHMENT_TITLE = "Screenshot {}"
ATTACHMENT_FILE_NAME = "{}.png"
CASE_WALL_TABLE_NAME = "{} - Search Results"
# CASE WALL CONSTANTS FOR URLCHECK ACTION
REPORT_LINK_TITLE = "Web Report - {}"
SCREENSHOT_TITLE = "Screenshot - {}"

# DATA MAPPER
VISIBILITY_MAPPER = {"public": "public", "unlisted": "unlisted", "private": "private"}


SEVERITIES_COLORS = {"high": "#de2026", "low": "#12ab50"}

URL_INSIGHT_HTML_TEMPLATE = """

<h2>Score: <span style="color: {severity_color}">{score}</span></h2>
<p><strong>Effective URL: {url}</p>
<p>This website contacted <strong>{number_of_ips}</strong> IPs in <strong>{number_of_countries}</strong> countries across <strong>{number_of_domains}</strong> domains to perform <strong>{number_od_transactions}</strong> HTTP transactions. The main IP is <strong>{ip_address}</strong>, located in <strong>{city}</strong>, <strong>{country}</strong> and belongs to <strong>{asnname}</strong>. The main domain is <strong>{domain}</strong>.<br /><br />TLS certificate: Issued by <strong>{certificate_issuer}</strong> on <strong>{certificate_valid_from}</strong>. Valid till <strong>{certificate_valid_to}</strong>.</p>
<h3>Screenshot</h3>
{screenshot}
"""
