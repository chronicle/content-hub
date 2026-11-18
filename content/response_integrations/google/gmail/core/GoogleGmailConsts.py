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
INTEGRATION_IDENTIFIER = "Gmail"
INTEGRATION_DISPLAY_NAME = "Gmail"

# Actions
ADD_EMAIL_LABEL_SCRIPT_NAME = "Add Email Label"
PING_SCRIPT_NAME = "Ping"
DELETE_EMAIL_SCRIPT_NAME = "Delete Email"
FORWARD_EMAIL_SCRIPT_NAME = "Forward Email"
REMOVE_EMAIL_LABEL_SCRIPT_NAME = "Remove Email Label"
SAVE_EMAIL_TO_THE_CASE = "Save Email To The Case"
SEND_EMAIL_SCRIPT_NAME = "Send Email"
SEND_THREAD_REPLY_SCRIPT_NAME = "Send Thread Reply"
SEARCH_FOR_EMAILS_SCRIPT_NAME = "Search For Emails"
WAIT_FOR_THREAD_REPLY_SCRIPT_NAME = "Wait For Thread Reply"

# Connectors
GOOGLE_GMAIL_CONNECTOR = "Google Gmail Connector"

OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://mail.google.com/",
]

# Error Codes
INVALID_ARGUMENT = "INVALID_ARGUMENT"
NOT_FOUND = "NOT_FOUND"
PERMISSION_DENIED = "PERMISSION_DENIED"
INTERNAL_SERVER_ERROR = "INTERNAL"

PROJECT_LOOKUP_ERROR_MESSAGE = "Project lookup error"
THROTTLING_OVERLOAD_MESSAGE = "throttling::OVERLOADED"

DEVICE_PRODUCT = "Gmail"
VENDOR = "Google"
CASE_NAME_PATTERN = "Gmail Monitored Mailbox <{}>"
PRIORITY_DEFAULT = 40

FIELDS_TO_EXTRACT = [
    "date",
    "to",
    "cc",
    "bcc",
    "in-reply-to",
    "reply-to"
]
REQUIRED_HEADERS = [
    "date",
    "from",
    "to",
    "cc",
    "bcc",
    "in-reply-to",
    "reply-to",
    "message-id",
    "subject",
]

KEYS_TO_EXCEPT_ON_TRANSFORMATION = [
    "device_product",
    "device_vendor",
    "event_name",
    "monitored_mailbox_name",
    "original_email_id",
]
ATTACHED_EMAIL_EVENT_NAME = "Attached Email File"
ORIGINAL_EMAIL_EVENT_NAME = "Email Received in Monitoring Mailbox"
MAX_EMAILS_PER_CYCLE_LIMIT = 100
DEFAULT_MAILBOX = "Default Mailbox"
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
MAX_LIST_RESULTS = 1000
REGEX_DATETIME_STR = r"\d{1,2} \w{3} \d{4} \d{2}:\d{2}:\d{2} (-|\+)\d{4}"
DATETIME_FORMAT = "%d %b %Y %H:%M:%S %z"

# language=html
FORWARD_EMAIL_TEMPLATE = """<br><br>
<div class=3D"gmail_quote">
    <div dir=3D"ltr" class=3D"gmail_attr">---------- Forwarded message ---------<br>
        From: {from_}<br>
        Date: {date}<br>
        Subject: {subject}<br>
        To: {to}<br>
    </div><br><br>
    <div dir=3D"ltr">{content}</div>
</div>
"""
