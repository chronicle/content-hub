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
INTEGRATION_NAME = "Lastline"

# Actions:
PING = "Ping"
SUBMIT_URL = "Submit URL"
SUBMIT_FILE = "Submit File"
SEARCH_ANALYSIS_HISTORY = "Search Analysis History"
GET_ANALYSIS_RESULTS = "Get Analysis Results"

SUCCESS_CODE = 1

# API Error codes:
PERMISSION_DENIED = 3001
AUTHENTICATION_ERROR = 3004
INVALID_PARAMETER_ERROR = 3005
NO_SUCH_ENTITY = 3007
NOT_YET_AVAILABLE = 3013
TOO_MANY_REQUESTS_ERROR = 3014
HOSTED_BACKEND_UNVAILABLE = 3015

DEFAULT_MAX_HOURS_BACKWARDS = 24
DEFAULT_X_LAST_SCANS = 100
DEFAULT_X_LAST_SCANS_GET_RESULTS = 25
DEFAULT_SKIP_X_FIRST_SCANS = 0
THRESHOLD = 70

MD5_LENGTH = 32
SHA1_LENGTH = 40

SUBMISSION_TYPE_MAPPER = {"URL": "URL", "FileHash": "FILE"}

NOT_SPECIFIED = "Not specified"
FILE = "FILE"
URL = "URL"

ANALYSIS_REPORT = "Lastline File Analysis Results"
SEARCH_RESULTS = "Search Results"
ANALYSIS_RESULTS = "{0} Analysis Results"
