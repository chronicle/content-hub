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
INTEGRATION_NAME = "Twilio"
PING_ACTION = f"{INTEGRATION_NAME} - Ping"
SEND_SMS_ACTION = f"{INTEGRATION_NAME} - SendSMS"
SEND_SMS_AND_WAIT_ACTION = f"{INTEGRATION_NAME} - Send SMS and Wait"
ID_GENERATION_START = 10_000
ID_GENERATION_END = 999_999
