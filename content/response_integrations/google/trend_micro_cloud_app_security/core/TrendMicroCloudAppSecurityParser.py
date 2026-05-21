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
from .datamodels import *


class TrendMicroCloudAppSecurityParser:

    @staticmethod
    def build_siemplify_blocked_entities_object(raw_data):

        return BlockedEntitiesObject(
            raw_data=raw_data,
            senders=raw_data.get("rules", {}).get("senders"),
            urls=raw_data.get("rules", {}).get("urls"),
            hashes=raw_data.get("rules", {}).get("filehashes"),
        )

    @staticmethod
    def build_siemplify_email_object(raw_data):

        emails = raw_data.get("value")

        return [
            EmailObject(
                raw_data=raw_data,
                email_value_data=email,
                mail_unique_id=email.get("mail_unique_id"),
                mailbox=email.get("mailbox"),
                mail_message_delivery_time=email.get("mail_message_delivery_time"),
            )
            for email in emails
        ]

    @staticmethod
    def build_siemplify_mitigation_status_object(raw_data):

        return MitigationStatus(
            raw_data=raw_data,
            code=raw_data.get("code"),
            msg=raw_data.get("msg"),
            batch_id=raw_data.get("batch_id"),
            trace_id=raw_data.get("trace_id"),
        )

    @staticmethod
    def build_siemplify_mitigation_results_object(raw_data):

        actions = raw_data.get("actions")
        return [
            MitigationDetails(
                raw_data=action,
                status=action.get("status"),
                error_code=action.get("error_code"),
                error_message=action.get("error_message"),
                account_user_email=action.get("account_user_email"),
            )
            for action in actions
        ]
