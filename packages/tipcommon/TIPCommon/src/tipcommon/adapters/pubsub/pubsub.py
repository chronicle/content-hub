# Copyright 2025 Google LLC
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

import base64
import json
from urllib.parse import urljoin

import requests

from ...exceptions import NotFoundError
from ...filters import filter_none_kwargs
from ...rest.httplib import get_auth_session
from ...transformation import convert_list_to_comma_string
from . import consts
from .data_models import PubSubMessage
from .parser import PubSubParser


class PubSubAdapter:
    """Adapter class for managing Google Cloud project pub/sub topics
    and subscriptions
    """

    def __init__(
        self,
        session,
        project_id=None,
        logger=None,
        region=None,
    ):
        self.logger = logger
        self.project_id = project_id
        self.session = session
        self.session.headers.update({"content-type": "application/json"})
        self.region = region

    @staticmethod
    def from_credentials(
        credentials,
        project_id=None,
        verify_ssl=True,
        quota_project=None,
        logger=None,
        region=None,
    ):
        """Creates `PubSubAdapter` object from
        `google.oauth2.credentials.Credentials` object.

        Args:
            credentials (google.oauth2.credentials.Credentials):
                A `google.oauth2.credentials.Credentials` object
            project_id (str | Optional):
                GCP project id. if not given, will try using
                the project configured in the credentials object
            verify_ssl (bool | Optional):
                verify ssl on http session
            quota_project (str | Optional):
                project to be used for quota and billing
            logger (SiemplifyLogger | Optional):
                a ``SiemplifyLogger`` logger object
            region (str | None): region for Pub/Sub to work in

        Returns:
            PubSubAdapter: A `PubSubAdapter` object

        """
        project_id = project_id or credentials.quota_project_id
        session = get_auth_session(
            credentials=credentials, audience=consts.PUBSUB_SCOPE, verify_ssl=verify_ssl
        )
        if quota_project is not None:
            session.headers.update({"x-goog-user-project": quota_project})
        return PubSubAdapter(
            session=session,
            project_id=project_id,
            logger=logger,
            region=region,
        )

    @staticmethod
    def from_service_account_info(
        user_service_account, project_id=None, verify_ssl=True, quota_project=None, logger=None
    ):
        """Creates `PubSubAdapter` object from service_account json.

        Args:
            user_service_account (str):
                GCP Service Account json in text format
            project_id (str | Optional):
                GCP project id. if not given, will try using
                the project configured in the credentials object
            verify_ssl (bool | Optional):
                verify ssl on http session
            quota_project (str | Optional):
                project to be used for quota and billing
            logger (SiemplifyLogger | Optional):
                a ``SiemplifyLogger`` logger object

        Returns:
            PubSubAdapter: A `PubSubAdapter` object

        """
        parsed_service_account = json.loads(user_service_account)
        project_id = project_id or parsed_service_account["project_id"]
        session = get_auth_session(
            service_account=parsed_service_account,
            audience=consts.PUBSUB_SCOPE,
            verify_ssl=verify_ssl,
        )
        if quota_project is not None:
            session.headers.update({"x-goog-user-project": quota_project})
        return PubSubAdapter(session=session, project_id=project_id, logger=logger)

    def _get_full_url(self, endpoint, **kwargs):
        """Build full request uri."""
        rep_subdomain = f".{self.region}.rep" if self.region is not None else ""
        return urljoin(
            base=consts.PUBSUB_API_ROOT.format(rep_subdomain=rep_subdomain),
            url=consts.PUBSUB_ENDPOINTS[endpoint].format(**kwargs),
        )

    @staticmethod
    def _validate_response(response):
        """Validates an http response from GCP PubSub API
        Args:
            response (requests.Response): HTTP response object
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as e:
            try:
                response_json = response.json()
                status = response_json.get("error", {}).get("status")
                if status in consts.PUBSUB_ERROR_STATUS_MAPPING:
                    exception = consts.PUBSUB_ERROR_STATUS_MAPPING[status]
                    msg = response_json.get("error", {}).get("message", "")
                    details = response_json.get("error", {}).get("details", [])
                    if details:
                        msg += " - {}".format(details[0].get("detail"))
                    raise exception(msg)
            except (json.JSONDecodeError, IndexError):
                # we don't care about these errors, so pass in order to
                # raise the original error
                pass

            if response.status_code == 502:
                raise (consts.PUBSUB_ERROR_STATUS_MAPPING["BAD_GATEWAY"](str(e))) from e

            raise e

    def _build_patch_mask_from_args(self, *fields):
        """Creates a patch mask to send in patch api request from updated fields

        Args:
            *fields:
                field names to update in pubsub resource via patch api request

        Returns:
            str: patch mask of the fields to update

        Raises:
             NotFoundError: if a field provided can't be identified with a mask

        """
        mask = []
        for field in fields:
            try:
                mask.append(consts.PUBSUB_FIELD_MASK_MAPPING[field])
            except Exception:
                raise NotFoundError(f'"{field}" is not a valid field for pubsub resource')
        return convert_list_to_comma_string(mask)

    def create_topic(self, topic_name):
        """Creates a pub/sub Topic in a GCP Project

        Args:
            topic_name (str):
                Name of the topic to be created.
                must correspond to GCP resource name rules
                (https://cloud.google.com/pubsub/docs/admin#resource_names).

        Returns:
             Topic:
                ``TIPCommon.adapters.pubsub.Topic`` object of the created topic.

        """
        url = self._get_full_url("topic", project_id=self.project_id, topic_name=topic_name)

        topic_ = {"name": f"projects/{self.project_id}/topics/{topic_name}"}
        if self.region is not None:
            topic_["message_storage_policy"] = {
                "allowedPersistenceRegions": [self.region],
                "enforceInTransit": True,
            }

        response = self.session.put(url, json=topic_)
        self._validate_response(response)
        return PubSubParser.build_topic_object(response.json())

    def delete_topic(self, topic_name):
        """Delete a pub/sub Topic from a GCP Project

        Args:
            topic_name (str): The topic to be removed

        """
        url = self._get_full_url("topic", project_id=self.project_id, topic_name=topic_name)
        response = self.session.delete(url)
        self._validate_response(response)

    def get_topic(self, topic_name, create_if_not_exist=False):
        """Retrieves a pub/sub topic object from the configured GCP project

        Args:
            topic_name (str):
                Name of the topic
                (simplified - without the`projects/{project_id}/topics/` prefix)
            create_if_not_exist (bool):
                Create the pub/sub topic in GCP, if it does not exist

        Returns:
            Topic:
                ``TIPCommon.adapters.pubsub.Topic`` object of the received topic.

        """
        url = self._get_full_url("topic", project_id=self.project_id, topic_name=topic_name)
        try:
            response = self.session.get(url)
            self._validate_response(response)
        except NotFoundError:
            if create_if_not_exist:
                return self.create_topic(topic_name)
            raise
        return PubSubParser.build_topic_object(response.json())

    def patch_topic(
        self,
        topic_name,
        labels=None,
        message_storage_policy=None,
        kms_key_name=None,
        schema_settings=None,
        satisfies_pzs=None,
        retention_duration=None,
    ):
        """Updates an existing topic.

        Notes:
            Certain properties of a topic are not modifiable.

        Args:
            topic_name (str):
                topic name

        Returns:
            Topic:
                ``TIPCommon.adapters.pubsub.Topic`` object of the received
                topic.

        """
        updated_fields = filter_none_kwargs(
            labels=labels,
            message_storage_policy=message_storage_policy,
            kms_key_name=kms_key_name,
            schema_settings=schema_settings,
            satisfies_pzs=satisfies_pzs,
            retention_duration=retention_duration,
        )
        url = self._get_full_url("topic", project_id=self.project_id, topic_name=topic_name)
        payload = {
            "topic": {"name": self.topic_name(self.project_id, topic_name)}.update(updated_fields),
            "updateMask": self._build_patch_mask_from_args(*updated_fields),
        }
        response = self.session.patch(url, json=payload)
        self._validate_response(response)
        return PubSubParser.build_topic_object(response.json())

    def create_subscription(self, sub_name, topic, **attr):
        """Creates a pubsub subscription for the specified topic

        Args:
            sub_name (str):
                Subscription name identifier
            topic (str):
                pubsub topic name create a subscription for
            **attr:
                Additional parameters to pass to the `Subscription` request

        Returns:
            Subscription:
                ``TIPCommon.adapters.pubsub.Subscription`` object of the
                created Subscription.

        """
        url = self._get_full_url("subscription", project_id=self.project_id, sub_name=sub_name)
        payload = {"topic": self.topic_name(self.project_id, topic)}
        if attr:
            payload.update(attr)

        response = self.session.put(url, json=payload)
        self._validate_response(response)
        return PubSubParser.build_subscription_object(response.json())

    def delete_subscription(self, sub_name):
        """Delete a pub/sub Subscription from a GCP Project

        Args:
            sub_name (str): The Subscription name to remove

        """
        url = self._get_full_url("subscription", project_id=self.project_id, sub_name=sub_name)
        response = self.session.delete(url)
        self._validate_response(response)

    def get_subscription(self, sub_name, topic=None, create_if_not_exist=False, **attr):
        """Retrieves a pubsub subscription

        Args:
            sub_name (str):
                Subscription name identifier
            topic (str):
                pubsub topic name to create a subscription for. Mandatory if
                `create_if_not_exist` is``True``
            create_if_not_exist:
                Create the pub/sub subscription in GCP, if it does not exist
            **attr:
                Additional parameters to pass to the `Subscription`
                creation request

        Returns:
            Subscription:
                ``TIPCommon.adapters.pubsub.Subscription`` object of the
                retrieved Subscription.

        """
        url = self._get_full_url("subscription", project_id=self.project_id, sub_name=sub_name)

        try:
            response = self.session.get(url)
            self._validate_response(response)
        except NotFoundError:
            if create_if_not_exist:
                return self.create_subscription(sub_name, topic, **attr)
            raise
        return PubSubParser.build_subscription_object(response.json())

    def patch_subscription(
        self,
        sub_name,
        topic_name,
        push_config=None,
        bigquery_config=None,
        cloud_storage_config=None,
        ack_deadline_seconds=None,
        retain_acked_messages=None,
        retention_duration=None,
        labels=None,
        enable_message_ordering=None,
        expiration_policy=None,
        query_filter=None,
        dead_letter_policy=None,
        return_policy=None,
        detached=None,
        enable_once_delivery=None,
    ):
        """Updates an existing topic

        Notes:
            Certain properties of a subscription are not modifiable.

        Args:
            sub_name (str):
                subscription name
            topic_name (str):
                The name of the topic from which this subscription is
                receiving messages

        Returns:
            Subscription:
                ``TIPCommon.adapters.pubsub.Subscription`` object of the
                received Subscription.

        """
        updated_fields = filter_none_kwargs(
            push_config=push_config,
            bigquery_config=bigquery_config,
            cloud_storage_config=cloud_storage_config,
            ack_deadline_seconds=ack_deadline_seconds,
            retain_acked_messages=retain_acked_messages,
            retention_duration=retention_duration,
            labels=labels,
            enable_message_ordering=enable_message_ordering,
            expiration_policy=expiration_policy,
            filter=query_filter,
            dead_letter_policy=dead_letter_policy,
            return_policy=return_policy,
            detached=detached,
            enable_once_delivery=enable_once_delivery,
        )
        url = self._get_full_url("subscription", project_id=self.project_id, sub_name=sub_name)
        payload = {
            "subscription": {
                "name": self.subscription_name(self.project_id, sub_name),
                "topic": self.topic_name(self.project_id, topic_name),
            },
            "updateMask": self._build_patch_mask_from_args(*updated_fields),
        }
        payload["subscription"].update(updated_fields)
        response = self.session.patch(url, json=payload)
        self._validate_response(response)
        return PubSubParser.build_subscription_object(response.json())

    def publish(self, topic_name, messages):
        """Publish a list of `PubSubMessage` objects to a topic

        Args:
            topic_name (str):
                Name of The topic to publish the messages.
            messages (list):
                list of `PubSubMessage` objects. Can be created with the
                ``PubSubAdapter.build_message()`` static method

        Returns:
            list[str]: List of message ids.

        """
        url = self._get_full_url("publish", project_id=self.project_id, topic_name=topic_name)
        if messages:
            messages = [msg.json() if isinstance(msg, PubSubMessage) else msg for msg in messages]
        payload = {"messages": messages}
        response = self.session.post(url, json=payload)
        self._validate_response(response)
        return PubSubParser.build_message_ids_list(response.json())

    def pull(self, sub_name, limit, timeout=60, encoding="utf-8"):
        """Pull messages from a pubsub subscriptions

        Args:
            sub_name (str):
                The subscription name
            limit (int):
                The maximum number of messages to return for this request
            timeout (int):
                HTTP request timeout in seconds. Defaults to 60
            encoding (str):
                pubsub message encoding. defaults to 'utf-8'

        Returns:
            list[ReceivedMessage]:
                List of ``TIPCommon.adapters.pubsub.ReceivedMessage`` objects

        """
        url = self._get_full_url("pull", project_id=self.project_id, sub_name=sub_name)
        payload = {"maxMessages": limit}
        response = self.session.post(url, json=payload, timeout=timeout)
        self._validate_response(response)
        return PubSubParser.build_received_messages_list(response.json(), encoding)

    def ack(self, sub_name, ack_ids):
        """Acknowledges the messages associated with the `ackIds` in the
        `AcknowledgeRequest` response returned from `PubSubAdapter.pull()`

        Args:
            sub_name (str):
                The subscription name
            ack_ids (list[str]):
                List of acknowledgment IDs (str) for the messages being
                acknowledged that was returned by the Pub/Sub system in the
                `PubSubAdapter.pull()` response

        """
        url = self._get_full_url("ack", project_id=self.project_id, sub_name=sub_name)
        payload = {"ackIds": ack_ids}
        response = self.session.post(url, json=payload)
        self._validate_response(response)

    @staticmethod
    def topic_name(project_id, topic):
        """Retrieves 'projects/{project_id}/topics/{topic_name}'
        Args:
            project_id (str): the project name containing this resource
            topic (str): pubsub topic name

        Returns:
            str: full topic name `projects/{project_id}/topics/{topic_name}`

        """
        return consts.PUBSUB_RESOURCE_TEMPLATE.format(
            project_id=project_id, resource_type="topics", resource_name=topic
        )

    @staticmethod
    def subscription_name(project_id, sub_name):
        """Retrieves the full subscription name in the format
        `projects/{project_id}/subscriptions/{subscription_name}`

        Args:
            project_id (str): the project name containing this resource
            sub_name (str): pub/sub subscription name

        Returns:
            str: full subscription name in the format
            `projects/{project_id}/subscriptions/{subscription_name}`

        """
        return consts.PUBSUB_RESOURCE_TEMPLATE.format(
            project_id=project_id, resource_type="subscriptions", resource_name=sub_name
        )

    @staticmethod
    def build_pubsub_message(message_content, encoding="utf-8", ordering_key=None, **attr):
        """Creates a PubSubMessage object

        Args:
            message_content (str):
                Message text content
            encoding (str):
                Encoding type to encode/decode the message text.
                Defaults to 'utf-8'
            ordering_key (str):
                Optional. If non-empty, identifies related messages for which
                publish order should be respected
            **attr:
                Optional (str). Attributes to pass as message object attributes
        Returns:
            PubSubMessage: ``TIPCommon.adapters.pubsub.PubSubMessage`` object

        """
        message = {"data": base64.b64encode(message_content.encode(encoding)).decode(encoding)}
        if ordering_key:
            message["orderingKey"] = ordering_key
        if attr:
            message["attributes"] = {k: str(v) for k, v in attr.items()}
        return PubSubParser.build_pub_sub_message_object(message, encoding)
