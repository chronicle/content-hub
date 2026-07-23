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

from TIPCommon.adapters import PubSubAdapter
from TIPCommon.adapters.pubsub.data_models import Subscription
from TIPCommon.base.utils import NewLineLogger
from TIPCommon.rest.auth import get_auth_request
from ..core import PubSubConstants as Constants
from ..core import PubSubDatamodels as DataModels


class ApiManager:
    def __init__(
        self,
        pubsub_client: PubSubAdapter,
        logger: NewLineLogger,
    ) -> None:
        """Manager for handling API interactions

        This class provides functionality for managing API interactions

        Args:
            pubsub_client: initialized Pub/Sub Client
            logger: The logger object
        """
        self.pubsub_client = pubsub_client
        self.logger = logger

    def test_connectivity(self) -> None:
        """Test connectivity."""
        self.pubsub_client.session.credentials.refresh(
            get_auth_request(self.pubsub_client.session.verify)
        )

    def pull_messages(
            self,
            alert_config: DataModels.AlertConfig,
            subscription: Subscription,
            max_alerts_to_fetch: int
    ) -> list[DataModels.PubSubMessage]:
        """
        Get new messages from subscription

        Args:
            alert_config: SOAR alert configuration for parsing
            subscription (TIPCommon.adapters.pubsub.Subscription):
                A `TIPCommon.adapters.pubsub.Subscription` object
            max_alerts_to_fetch (int):
                Maximum number of findings to fetch

        Returns:
            list[datamodels.PostureAlert]:
                A list of `datamodels.PostureAlert` alert objects
        """
        pubsub_messages = self.pubsub_client.pull(
            sub_name=subscription.name,
            limit=max_alerts_to_fetch,
            timeout=Constants.PUB_SUB_PULL_TIMEOUT
        )
        filtered_pubsub_messages = []
        test_ack_ids = []
        for pubsub_message in pubsub_messages:
            # This is a test message that might be sent by pubsub
            if pubsub_message.message.data == "Test":
                self.logger.info(
                    "Received a test message, adding to ack queue ..."
                )
                test_ack_ids.append(pubsub_message.ack_id)
                continue

            filtered_pubsub_messages.append(
                DataModels.PubSubMessage(
                    pubsub_message,
                    alert_config=alert_config,
                    logger=self.logger,
                )
            )

        self.ack_pubsub_findings(subscription.name, test_ack_ids)
        return filtered_pubsub_messages

    def get_subscription(
            self,
            subscription_name: str,
            ack_deadline: int,
    ) -> Subscription:
        """Gets a GCP pubsub subscription.

        Args:
            subscription_name (str):
                Subscription name.
            ack_deadline (int):
                amount of seconds Pub/Sub waits for the subscriber to
                acknowledge receipt before resending the message

        Returns:
            TIPCommon.adapters.pubsub.Subscription:
                `TIPCommon.adapters.pubsub.Subscription` object
        """
        sub_configs = {}
        if ack_deadline:
            sub_configs["ackDeadlineSeconds"] = ack_deadline

        sub = self.pubsub_client.get_subscription(
            sub_name=subscription_name,
            **sub_configs
        )

        if sub.ack_deadline_secs != ack_deadline:
            self.logger.info(
                f"Subscription {subscription_name} has outdated ackDeadlineSeconds "
                f"value, updating to {ack_deadline} ..."
            )
            sub = self.pubsub_client.patch_subscription(
                sub_name=subscription_name,
                topic_name=sub.topic_identifier,
                ack_deadline_seconds=ack_deadline
            )

        return sub

    def ack_pubsub_findings(self, sub_name: str, ack_ids: list[str]) -> None:
        """Acknowledge findings fetched from pubsub

        Args:
            sub_name (str):
                the simple name of the pubsub subscription
            ack_ids (list[str]):
                List of pubsub received messages ack_ids
        """
        if ack_ids:
            self.pubsub_client.ack(
                sub_name=sub_name,
                ack_ids=ack_ids
            )
