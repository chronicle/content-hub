from __future__ import annotations

import json
import re
from typing import Any, Callable
from urllib.parse import urljoin

from google.auth.exceptions import RefreshError
import google.auth.transport.requests as google_requests

from TIPCommon.adapters import PubSubAdapter
from TIPCommon.base.utils import CreateSession
from TIPCommon.exceptions import NotFoundError
from TIPCommon.rest.auth import build_credentials_from_sa
from TIPCommon.rest.gcp import retrieve_project_id
from TIPCommon.rest.gcp import get_workload_sa_email
from TIPCommon.types import ChronicleSOAR, SingleJson
from TIPCommon.utils import is_empty_string_or_none

from scc_enterprise.core.GoogleSecurityCommandCenterParser import GoogleSecurityCommandCenterParser
from scc_enterprise.core.GoogleSecurityCommandCenterExceptions import (
    GoogleSecurityCommandCenterException,
    GoogleSecurityCommandCenterNotFound,
)
from scc_enterprise.core.GoogleSecurityCommandCenterUtilsManager import (
    parse_string_to_dict,
    validate_response,
)
from scc_enterprise.core.GoogleSecurityCommandCenterConstants import (
    API_ROOT_REGEX,
    ENDPOINTS,
    ORIGIN_HEADERS,
    PUB_SUB_PULL_TIMEOUT,
    SCOPES,
)
from scc_enterprise.core.GoogleSecurityCommandCenterDatamodels import FindingDetails, Source

from scc_enterprise.core.SCCEnterpriseExceptions import ProjectNotFound
from scc_enterprise.core.SCCEnterpriseUtils import (
    get_scce_sa_email,
    get_scce_tenant_credentials,
    parse_project_from_sa,
    add_params_to_url,
)


class GoogleSecurityCommandCenterManager:
    def __init__(
        self,
        api_root: str,
        organization_id: str,
        location_id: str,
        service_account_string: str | None,
        workload_identity_email: str | None,
        verify_ssl: bool,
        pubsub_project_id: str | None = None,
        quota_project_id: str | None = None,
        chronicle_soar: ChronicleSOAR | None = None,
    ):
        """
        The method is used to init an object of Manager class

        Args:
            api_root (str): API root
            organization_id (str): organization id
            location_id (str): location id
            pubsub_project_id (str): project id of the pubsub
            quota_project_id (str): project id to use for SCC API quota
            service_account_string (str):
                JSON string containing service account info
            workload_identity_email (str):
                SA Email to be used for workload identity impersonation
            verify_ssl (bool):
                Specifies if certificate that is configured on the api root
                should be validated
            chronicle_soar (ChronicleSOAR): Chronicle SOAR SDK object
        """
        api_root_match = re.match(API_ROOT_REGEX, api_root)
        if api_root_match is None:
            raise GoogleSecurityCommandCenterException(
                "Provided api root does not match expected regex pattern: "
                f"{API_ROOT_REGEX}"
            )

        self.api_root = api_root_match.group(0)
        self.region = api_root_match.group(3)
        self.global_api_root = (
            self.api_root if self.region is None
            else self.api_root.replace(api_root_match.group(2), "")
        )

        self.verify_ssl = verify_ssl
        self.organization_id = organization_id
        self.location_id = location_id or "global"
        self.pubsub_project_id = pubsub_project_id
        self.quota_project_id = quota_project_id
        self.service_account_json = (
            parse_string_to_dict(service_account_string)
            if not is_empty_string_or_none(service_account_string)
            else None
        )
        self.workload_identity_email = workload_identity_email
        self._scce_sa_client_email = None
        self.siemplify_logger = (
            chronicle_soar.LOGGER if chronicle_soar is not None else None
        )
        self.parser = GoogleSecurityCommandCenterParser()
        self.creds = None
        self.http_client = None
        self._pubsub_client = None
        self._init_creds(chronicle_soar)
        self._prepare_http_client()

    def _init_creds(self, chronicle_soar: ChronicleSOAR) -> None:
        """
        Initialize Credentials object for SCC backend api

        Args:
            chronicle_soar: Chronicle SOAR SDK object

        """
        if self.service_account_json is not None or not is_empty_string_or_none(
            self.workload_identity_email
        ):
            try:
                self.creds = build_credentials_from_sa(
                    self.service_account_json,
                    self.workload_identity_email,
                    scopes=SCOPES,
                    verify_ssl=self.verify_ssl,
                    quota_project_id=self.quota_project_id,
                )
                return

            except RefreshError as e:
                workload_sa = get_workload_sa_email("Principal Could not be found")
                raise GoogleSecurityCommandCenterException(
                    "Impersonation is not allowed for the provided service account "
                    f"{self.workload_identity_email}! In Order to use Workload Identity"
                    ' Email, add the "Service Account Token Creator" IAM Role to '
                    f"{workload_sa} on the desired Service Account"
                ) from e

        try:
            self._scce_sa_client_email = get_scce_sa_email(chronicle_soar)
            self.creds = get_scce_tenant_credentials(
                chronicle_soar=chronicle_soar,
                target_scopes=SCOPES,
                quota_project_id=self.quota_project_id,
            )

        except ProjectNotFound as e:
            raise GoogleSecurityCommandCenterException(
                "Authentication with Workload Identity to Google"
                "Security Command Center server resulted in failure. "
                f"Error: {e}."
            ) from e

    def _prepare_http_client(self):
        """
        Prepare http client
        """
        auth_session = CreateSession.create_session()
        auth_session.verify = self.verify_ssl
        self.http_client = google_requests.AuthorizedSession(
            self.creds, auth_request=google_requests.Request(session=auth_session)
        )
        self.http_client.verify = self.verify_ssl
        self.test_connectivity()

    def _get_full_url(self, url_id: str, **kwargs: str) -> str:
        """Get full url from url identifier.

        Args:
            url_id (str): The ID of thr URL
            kwargs (dict): Variables passed for string formatting

        Returns:
            str: The full URL
        """
        endpoint_ = ENDPOINTS[url_id].format(**kwargs)
        if "locations/" in endpoint_:
            return urljoin(self.api_root, endpoint_)
        return urljoin(self.global_api_root, endpoint_)

    def test_connectivity(self) -> bool:
        """Test connectivity to Google Security Command Center"""
        url = self._get_full_url(
            "ping", id=self.organization_id, location_id=self.location_id
        )
        response = self.http_client.get(url, headers=ORIGIN_HEADERS)
        validate_response(response)
        return True

    def list_findings_by_filter(
        self,
        filter_string: str,
        page_size: int = 100,
        order_by: str = "eventTime",
        order_direction_asc: bool = True,
        limit: int | None = None,
    ) -> list[FindingDetails]:
        """Get list of findings by filter

        Args:
            filter_string (str):
                Filter to be applied list findings endpoint
            page_size (int, optional):
                How many findings to return per page. Defaults to 100.
            order_by (str, optional):
                Order by field. Defaults to "eventTime".
            order_direction_asc (bool, optional):
                Order results in ascending or descending order. Defaults to True.
            limit (int, optional): How many findings to return in total.

        Returns:
            list[FindingDetails]: list of findings
        """
        url = self._get_full_url(
            "list_findings", id=self.organization_id, location_id=self.location_id
        )
        params = {
            "orderBy": order_by if order_direction_asc else f"{order_by} desc",
            "filter": filter_string,
        }

        return self._paginate_results(
            method="GET",
            url=url,
            parser_method=self.parser.build_finding_details_list,
            page_size=page_size,
            limit=limit,
            params=params,
        )

    def list_sources(self, page_size: int = 100) -> list[Source]:
        """Get list of sources

        Args:
            page_size (int, optional):
                How many sources to return per page. Defaults to 100.

        Returns:
            list[Source]: list of sources
        """
        url = self._get_full_url("list_sources", id=self.organization_id)

        return self._paginate_results(
            method="GET",
            url=url,
            parser_method=self.parser.build_sources_list,
            page_size=page_size,
        )

    def _paginate_results(
        self,
        method: str,
        url: str,
        parser_method: Callable[[SingleJson], list[Any]],
        page_size: int | None = None,
        limit: int | None = None,
        params: SingleJson | None = None,
        body: SingleJson | None = None,
    ) -> list[Any]:
        """Paginate results from SCC backend api

        Args:
            method (str):
                The method of the request (GET, POST, PUT, DELETE, PATCH, etc...)
            url (str):
                The url to send request to
            parser_method (Callable):
                The parser method to build the result
            page_size (int | None, optional):
                Items per page. Defaults to None.
            limit (int | None, optional):
                The limit of the results to fetch. Defaults to None.
            params (dict | None, optional):
                Request query params. Defaults to None.
            body (dict | None, optional):
                The json payload of the request. Defaults to None.

        Returns:
            list[Any]: The list of results
        """
        params = params or {}
        results = []
        done = False

        if page_size is not None:
            params["pageSize"] = page_size

        full_url = add_params_to_url(url, params)

        while not done:
            response = self.http_client.request(
                method, full_url, headers=ORIGIN_HEADERS, json=body
            )
            validate_response(response)
            results.extend(parser_method(response.json()))
            next_page_token = response.json().get("nextPageToken", None)
            if limit and len(results) >= limit:
                done = True
                results = results[:limit]
            elif next_page_token is not None:
                params["pageToken"] = next_page_token
                full_url = add_params_to_url(url, params)
            else:
                done = True

        return results

    def get_finding_details(self, finding_name: str) -> list[FindingDetails]:
        """
        Get finding details

        Args:
            finding_name (str): Name of the finding

        Returns:
            list: List of `FindingDetails` objects
        """
        url = self._get_full_url(
            "get_finding_details",
            id=self.organization_id,
            location_id=self.location_id,
            finding_name=finding_name,
        )
        response = self.http_client.request("GET", url, headers=ORIGIN_HEADERS)
        validate_response(response)

        return self.parser.build_finding_details_list(response.json())

    def update_finding_external_systems(
        self,
        external_system_name: str,
        external_systems_details: dict = None,
        field_mask: str | None = None,
        **fields_to_update,
    ) -> None:
        """Updates finding External system info in SCC

        Args:
            external_system_name (str):
                external system name. format:
                'organizations/{org_id}/sources/{source_id}/locations/{location_id}/'
                'findings/{finding_id}/externalSystems/{external_system_id}'
            external_systems_details (dict, optional):
                External Systems json. Defaults to {}.
            field_mask (str, optional):
                The FieldMask to use when updating the external system resource.
                Defaults to None.
            fields_to_update:
                key-value pairs of the external system attributes to update.
        """
        url = self._get_full_url(
            "update_finding_external_systems", external_system_name=external_system_name
        )
        if field_mask is not None:
            url += f"?updateMask={field_mask}"

        payload = external_systems_details or {}
        payload.update(fields_to_update)
        response = self.http_client.request(
            "PATCH", url, json=payload, headers=ORIGIN_HEADERS
        )
        validate_response(response)

    def get_posture_alerts(self, subscription, max_alerts_to_fetch):
        """
        Get Urgent posture findings from SCC pubsub subscription

        Args:
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
            timeout=PUB_SUB_PULL_TIMEOUT,
        )
        filtered_pubsub_messages = []
        test_ack_ids = []
        for pubsub_message in pubsub_messages:
            # This is a test message that might be sent by pubsub
            if pubsub_message.message.data == "Test":
                self.siemplify_logger.info(
                    f"Received a test message, adding to ack queue ..."
                )
                test_ack_ids.append(pubsub_message.ack_id)
            elif "asm_tags" in json.loads(pubsub_message.message.data).get(
                "finding", {}
            ).get("sourceProperties", {}):
                self.siemplify_logger.info(
                    f"Received a message pushed by ASM, adding to ack queue ..."
                )
                test_ack_ids.append(pubsub_message.ack_id)
            else:
                filtered_pubsub_messages.append(pubsub_message)
        self.ack_pubsub_findings(subscription.name, test_ack_ids)
        return self.parser.build_urgent_posture_findings_list(filtered_pubsub_messages)

    def get_pubsub_subscription(
        self,
        pubsub_topic_name: str,
        subscription_name: str,
        notifications_config_name: str | None = None,
        query_filter: str | None = None,
        toxic_query_filter: str | None = None,
        ack_deadline: int | None = None,
        toxic_notifications_config_name: str | None = None,
    ):
        """Gets a GCP pubsub subscription.

        Args:
            notifications_config_name (str):
                Notifications Config name.
            toxic_notifications_config_name (str):
                Notifications Config name for TC.
            pubsub_topic_name (str):
                Topic name.
            subscription_name (str):
                Subscription name.
            query_filter (str):
                query filter
            toxic_query_filter (str):
                toxic query filter
            ack_deadline (int):
                amount of seconds Pub/Sub waits for the subscriber to
                acknowledge receipt before resending the message

        Returns:
            TIPCommon.adapters.pubsub.Subscription:
                `TIPCommon.adapters.pubsub.Subscription` object
        """
        # Reformat identifier to be applicable for both topic and notification creation
        # Topic / Subscription -> https://cloud.google.com/pubsub/docs/admin#resource_names
        # Notification -> The config_id  should be between 1 and 128 characters,
        # and should only contain characters that are alphanumeric, underscores, or hyphens.
        regular_created, toxic_created = False, False

        try:
            topic = self.pubsub_client.get_topic(topic_name=pubsub_topic_name)
        except NotFoundError:
            self.siemplify_logger.info(
                f"Pubsub topic {pubsub_topic_name} does not exists in project "
                f"{self.pubsub_project_id}. Creating topic"
            )
            topic = self.pubsub_client.create_topic(pubsub_topic_name)

        if notifications_config_name and query_filter:
            regular_created = self._get_or_update_notification_config(
                notifications_config_name=notifications_config_name,
                query_filter=query_filter,
                pubsub_topic=topic.identifier,
            )

        if toxic_notifications_config_name and toxic_query_filter:
            toxic_created = self._get_or_update_notification_config(
                query_filter=toxic_query_filter,
                notifications_config_name=toxic_notifications_config_name,
                pubsub_topic=topic.identifier,
            )

        if regular_created or toxic_created:
            self.__delete_legacy_notifications_config(notifications_config_name)
            self.__delete_legacy_notifications_config(toxic_notifications_config_name)

        return self._get_or_update_subscription(
            sub_name=subscription_name, topic_name=topic.name, ack_deadline=ack_deadline
        )

    def _get_or_update_subscription(self, sub_name, topic_name, ack_deadline=None):
        """Get or Update / Create subscription with provided params.

        Args:
            sub_name (str):
                the simple name of the pubsub subscription
            topic_name (str):
                List of pubsub received messages ack_ids
            ack_deadline (int):
                Ack deadline to be set for subscription

        Returns:
            TIPCommon.adapters.pubsub.Subscription:
                `TIPCommon.adapters.pubsub.Subscription` object
        """
        sub_configs = {}
        if ack_deadline:
            sub_configs["ackDeadlineSeconds"] = ack_deadline

        sub = self.pubsub_client.get_subscription(
            sub_name=sub_name, topic=topic_name, create_if_not_exist=True, **sub_configs
        )

        if ack_deadline and sub.ack_deadline_secs != ack_deadline:
            self.siemplify_logger.info(
                f"Subscription  {sub_name} has outdated ackDeadlineSeconds "
                f"value, updating to - {ack_deadline}"
            )
            sub = self.pubsub_client.patch_subscription(
                sub_name=sub_name,
                topic_name=topic_name,
                ack_deadline_seconds=ack_deadline,
            )

        return sub

    def ack_pubsub_findings(self, sub_name, ack_ids):
        """Acknowledge findings fetched from pubsub

        Args:
            sub_name (str):
                the simple name of the pubsub subscription
            ack_ids (list[str]):
                List of pubsub received messages ack_ids
        """
        if ack_ids and self.pubsub_client is not None:
            self.pubsub_client.ack(sub_name=sub_name, ack_ids=ack_ids)

    def _get_or_update_notification_config(
        self, notifications_config_name: str, query_filter: str, pubsub_topic: str
    ) -> bool:
        """Get or Update a notification config for a pubsub topic based on filter_query.

        Ensure this ServiceAccount has the "pubsub.topics.setIamPolicy"
        permission on the new topic.

        Args:
            notifications_config_name (str): Notifications config name
            query_filter: SCC query filter for streamingConfig
            pubsub_topic: PubSub topic name

        Returns:
            bool: True if created, False otherwise
        """
        try:
            url = self._get_full_url(
                "get_notifications_config",
                id=self.organization_id,
                location_id=self.location_id,
                notifications_config_id=notifications_config_name,
            )
            response = self.http_client.request("GET", url, headers=ORIGIN_HEADERS)
            validate_response(response)
            notification_config = self.parser.build_notifications_config_object(
                response.json()
            )
            if notification_config.streaming_config.get("filter") != query_filter:
                self.siemplify_logger.info(
                    f"Notification config {notifications_config_name} filter have "
                    f"changed. Updating filter with - {query_filter}"
                )
                _ = self.__patch_notifications_config(
                    notification_config_name=notification_config.config_id,
                    update_mask=["streamingConfig.filter"],
                    streamingConfig={"filter": query_filter},
                )
        except GoogleSecurityCommandCenterNotFound:
            self.siemplify_logger.info(
                f"Notification config {notifications_config_name} does not exists."
                f" Creating new notification config"
            )
            _ = self.__create_notification_config(
                notification_config_id=notifications_config_name,
                pubsub_topic=pubsub_topic,
                query_filter=query_filter,
            )
            return True

        return False

    def __delete_legacy_notifications_config(
        self, notifications_config_id: str | None
    ) -> None:
        """Delete a v1 notification config.

        Args:
            notifications_config_id: Notifications config ID
        """
        if notifications_config_id is None:
            return

        try:
            url = self._get_full_url(
                "delete_legacy_notifications_config",
                id=self.organization_id,
                notifications_config_id=notifications_config_id,
            )
            response = self.http_client.request("DELETE", url, headers=ORIGIN_HEADERS)
            validate_response(response)
            self.siemplify_logger.info(
                f"V1 Notification config {notifications_config_id} was successfully "
                "removed."
            )
        except GoogleSecurityCommandCenterNotFound:
            self.siemplify_logger.info(
                f"V1 Notification config {notifications_config_id} was not found. "
                "Skipping..."
            )
        except GoogleSecurityCommandCenterException as e:
            self.siemplify_logger.info(
                "Error while deleting v1 notification config "
                f"{notifications_config_id}\nError is {e}"
            )

    def __patch_notifications_config(
        self, notification_config_name: str, update_mask: list, **kwargs
    ):
        """Patch a notification configuration with fields provided in kwargs.

        Args:
            notification_config_name: "projects/{project_id}/your-config-id"
            update_mask: [pubsubTopic, streamingConfig.filter]
            kwargs: Dict with all key value pairs for update

        Ensure this ServiceAccount has the "pubsub.topics.setIamPolicy"
        permission on the new topic.
        """
        url = self._get_full_url(
            "patch_notifications_config",
            notification_config_name=notification_config_name,
        )
        params = {"updateMask": ",".join(update_mask)}
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        response = self.http_client.request(
            "PATCH", url, json=kwargs, headers=ORIGIN_HEADERS
        )
        validate_response(response)
        return self.parser.build_notifications_config_object(response.json())

    def __create_notification_config(
        self, notification_config_id: str, pubsub_topic, query_filter: str
    ):
        """Create a notification configuration for a pubsub topic.

        Args:
            notification_config_id: "your-config-id"
            pubsub_topic: "projects/{your-project-id}/topics/{your-topic-id}"
            query_filter: SCC query filter for streamingConfig

        Ensure this ServiceAccount has the "pubsub.topics.setIamPolicy"
        permission on the new topic.
        """
        url = self._get_full_url(
            "create_notifications_config",
            id=self.organization_id,
            location_id=self.location_id,
        )
        params = {"configId": notification_config_id}
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        payload = {
            "description": "Urgent Posture Findings Pub/Sub topic",
            "pubsubTopic": pubsub_topic,
            "streamingConfig": {"filter": query_filter},
            "includeTags": True,
        }
        response = self.http_client.request(
            "POST", url, json=payload, headers=ORIGIN_HEADERS
        )
        validate_response(response)
        return self.parser.build_notifications_config_object(response.json())

    def _init_pubsub_client(self):
        """Initialize Pubsub Client for the manager object"""
        try:
            try:
                pubsub_project_id = self.pubsub_project_id or retrieve_project_id(
                    self.service_account_json, self.workload_identity_email
                )
                # retrieve_project_id can either return None or raise NotFoundError
                # when it didn't manage to resolve a project. We want to treat both
                # cases the same way.
                if pubsub_project_id is None:
                    raise NotFoundError

            except NotFoundError:
                pubsub_project_id = parse_project_from_sa(self._scce_sa_client_email)
                self.siemplify_logger.info(
                    "Project ID is empty or None. Trying to fallback to "
                    f"default project {pubsub_project_id}"
                )

            self._pubsub_client = PubSubAdapter.from_credentials(
                credentials=self.creds,
                project_id=pubsub_project_id,
                quota_project=self.quota_project_id,
                verify_ssl=self.verify_ssl,
                logger=self.siemplify_logger,
                region=self.region,
            )
        except ProjectNotFound as e:
            raise GoogleSecurityCommandCenterException(
                "Authentication with Workload Identity to Google"
                "Security Command Center server resulted in failure. "
                f"Error: {e}."
            ) from e

    @property
    def pubsub_client(self) -> PubSubAdapter:
        """
        Pubsub client property

        Returns:
            TIPCommon.adapters.pubsub.PubSubAdapter: `PubsubAdapter` object
        """
        if self._pubsub_client is None:
            self._init_pubsub_client()
        return self._pubsub_client
