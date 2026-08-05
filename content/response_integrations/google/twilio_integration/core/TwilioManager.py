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

# ==============================================================================
# title           :TwilioManager.py
# description     :This Module contain all Twilio cloud operations functionality
# author          :avital@siemplify.co
# date            :01-06-18
# python_version  :2.7
# libreries       : twilio
# requirments     :
# product_version :
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

# =====================================
#              CLASSES                #
# =====================================


class TwilioManagerError(Exception):
    """
    General Exception for Twilio manager
    """

    pass


class TwilioManager:
    """
    Responsible for all Twilio system operations functionality
    """

    def __init__(self, account_sid, token):
        self.client = Client(account_sid, token)

    def test_connectivity(self):
        """
        Test connectivity to Twilio
        :return: {bool} True if successful, exception otherwise.
        """
        try:
            self.list_messages(limit=1)
            return True

        except TwilioException as e:
            if e.args[1].status_code in [401, 404]:
                raise TwilioManagerError(
                    "Failed to connect to Twilio. Please verify your credentials."
                )
            raise

    def list_messages(
        self,
        to=None,
        from_=None,
        date_sent_after=None,
        date_sent_before=None,
        limit=None,
    ):
        """
        Fetch messages according to filters
        :param to: {str} The destination of the SMS
        :param from_: {str} The sender of the SMS
        :param date_sent_after: {str} RFC-2822 formatted date to search messages sent after
        :param date_sent_before: {str} RFC-2822 formatted date to search messages sent before
        :param limit: {int} The max num of messages to fetch
        :return: {list} The found messages
        """
        return self.client.messages.list(
            to=to,
            from_=from_,
            date_sent_after=date_sent_after,
            date_sent_before=date_sent_before,
            limit=limit,
        )

    def send_message(self, to, from_, body):
        """
        Send an SMS
        :param to: {str} The destination phone of the SMS
        :param from_: {str} The sender of the SMS
        :param body: {str} The message body of the SMS
        :return: {MessageInstance} twilio message object representing the sent SMS
        """
        return self.client.api.account.messages.create(to=to, from_=from_, body=body)
