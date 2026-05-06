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


class ObserveITPayload:
    @staticmethod
    def get_authorization_payload(client_id, client_secret):
        # type: (str or unicode, str or unicode) -> dict
        """Get payload dict to make request with
        @param client_id: Client ID to authorize with
        @param client_secret: Client Secret to authorize with
        @return: Payload for request
        """
        return {
            "data": {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "*",
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        }

    @staticmethod
    def get_test_connectivity_payload():
        # type: () -> dict
        """Get payload dict to make request with
        @return: Payload for request
        """
        return {}

    @staticmethod
    def get_alerts_payload(severities, timestamp, limit):
        # type: (str or unicode, int, int) -> dict
        """Get payload dict to make request with
        @param severities: Severities to start from
        @param timestamp: Timestamp to start from
        @param limit: How many alerts to take
        @return: Payload for request
        """
        severities_filter = ",".join(
            [f"eq(severity,{severity})" for severity in severities]
        )

        return {
            "params": {
                # TODO: Write a constructor for RQL.
                "rql": f"and(select(),or({severities_filter}),ge(risingValue,epoch:{timestamp}),limit({limit},0))"
            }
        }
