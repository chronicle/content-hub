from abc import ABC, abstractmethod
from typing import List
from urllib.parse import urlencode

import requests
from TIPCommon.types import Contains
from cached_property import cached_property

from .auth_managers import AuthManager, CloudInfraAuthManager, SmartAPIAuthManager


class APIBaseClient(ABC):

    auth_manager: Contains[AuthManager]
    verify_ssl: bool

    @cached_property
    def api_version(self):
        return self.auth_manager.api_version

    @cached_property
    def host(self):
        return self.auth_manager.host

    @abstractmethod
    def get_path(self, endpoint: str) -> str:
        pass

    @abstractmethod
    def get_request_string(self, endpoint: str, params: dict = None) -> str:
        pass

    def call_api(
            self,
            method: str,
            endpoint: str,
            params: dict = None,
            body: dict = None,
            headers: dict = None
    ) -> dict:
        """
        Perform call to the Smart API

        :param method: HTTP method - post, get
        :param endpoint: API Endpoint
        :param params: GET parameters
        :param body: JSON Body
        :param headers: Custom headers
        :return: Response JSON
        """
        headers = headers or self.auth_manager.headers(self.get_request_string(endpoint, params))
        res = requests.request(
            method,
            f'https://{self.host}/{self.get_path(endpoint)}',
            headers=headers,
            params=params,
            json=body,
            verify=self.verify_ssl
        )
        try:
            res.raise_for_status()

        except requests.exceptions.HTTPError as e:
            raise e

        self.json_results = res.json()
        return res.json()

    @staticmethod
    def strip_none(payload: dict):
        for key, value in dict(payload).items():
            if value is None:
                del payload[key]

    def get_scopes(self):
        """
        Get list of scopes available for app client (client_id + client_secret)
        Scopes are made of 2 values separated by ":", for example, mt-prod-3:customer1
        The first is the farm (internal designation), the second is your customer name used to access the
        portal.

        :return: List of scopes as <farm>:<customer>
        """
        return self.call_api('get', 'scopes')

    def get_event(self, event_id: str):
        """
        Get single SaaS entity

        :param event_id: Security Event ID
        :return: Security Event
        """
        return self.call_api('get', f'event/{event_id}')

    def query_events(
            self,
            start_date: str,
            end_date: str = None,
            event_types: List[str] = None,
            event_states: List[str] = None,
            severities: List[str] = None,
            saas: List[str] = None,
            description: str = None,
            event_ids: List[str] = None,
            scroll_id: str = None,
            scopes: List[str] = None
    ):
        """
        Query Security Events

        :param start_date: Start date (iso 8601)
        :param end_date: End date (iso 8601)
        :param event_types: List of event types
        :param event_states: List of event states
        :param severities: List of severities
        :param saas: SaaS Name
        :param description: Description
        :param event_ids: List of Event ID
        :param scroll_id: Scroll ID for pagination
        :param scopes: List of scopes as <farm>:<customer>
        :return: Security events
        """
        request_data = {
            'scopes': scopes,
            'eventTypes': event_types,
            'eventStates': event_states,
            'severities': severities,
            'startDate': start_date,
            'endDate': end_date,
            'saas': saas,
            'description': description,
            'eventIds': event_ids,
            'scrollId': scroll_id
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', 'event/query', body=payload)

    def get_entity(self, entity_id: str):
        """
        Get single SaaS entity

        :param entity_id: SaaS Entity ID
        :return: Entity
        """
        return self.call_api('get', f'search/entity/{entity_id}')

    def query_entities(
            self,
            saas: str,
            start_date: str,
            end_date: str = None,
            entity_type: str = None,
            extended_filter: List[dict] = None,
            scroll_id: str = None,
            scopes: List[str] = None
    ):
        """
        Query SaaS entities

        :param saas: SaaS Name
        :param start_date: Start date (iso 8601)
        :param end_date: End date (iso 8601)
        :param entity_type: SaaS Entity Type
        :param extended_filter: Extended filters list
        :param scroll_id: Scroll ID for pagination
        :param scopes: List of scopes as <farm>:<customer>
        :return: Entities
        """
        entity_filter = {
            'saas': saas,
            'saasEntity': entity_type,
            'startDate': start_date,
            'endDate': end_date,
        }
        self.strip_none(entity_filter)
        request_data = {
            'scopes': scopes,
            'entityFilter': entity_filter,
            'entityExtendedFilter': extended_filter,
            'scrollId': scroll_id
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', 'search/query', body=payload)

    def search_emails(
            self,
            start_date: str,
            end_date: str = None,
            saas: str = None,
            direction: str = None,
            subject_contains: str = None,
            subject_match: str = None,
            sender_contains: str = None,
            sender_match: str = None,
            domain: str = None,
            cp_detection: List[str] = None,
            ms_detection: List[str] = None,
            detection_op: str = None,
            server_ip: str = None,
            recipients_contains: str = None,
            recipients_match: str = None,
            links: str = None,
            message_id: str = None,
            cp_quarantined_state: str = None,
            ms_quarantined_state: str = None,
            quarantined_state_op: str = None,
            name_contains: str = None,
            name_match: str = None,
            client_ip: str = None,
            attachment_md5: str = None,
    ):
        """
        Search email entities with various filters

        :param start_date: Start date (iso 8601)
        :param end_date: End date (iso 8601)
        :param saas: SaaS Name
        :param direction: Email direction (internal/incoming/outgoing)
        :param subject_contains: Subject contains string
        :param subject_match: Subject match string
        :param sender_contains: Sender email contains string
        :param sender_match: Sender email match string
        :param domain: Sender domain
        :param cp_detection: Check Point detection categories
        :param ms_detection: Microsoft detection categories
        :param detection_op: Operator for combining Check Point and Microsoft detections (and/or)
        :param server_ip: Sender server IP
        :param recipients_contains: Recipients contains string
        :param recipients_match: Recipients match string
        :param links: Email links contains string
        :param message_id: Internet message ID
        :param cp_quarantined_state: Check Point quarantined state
        :param ms_quarantined_state: Microsoft quarantined state
        :param quarantined_state_op: Operator for combining Check Point and Microsoft quarantined states (and/or)
        :param name_contains: Sender name contains string
        :param name_match: Sender name match string
        :param client_ip: Sender client IP
        :param attachment_md5: Attachment MD5 hash
        return: Email entities matching the filters
        """

        entity_filter = {
            "saas": saas,
            "startDate": start_date,
        }
        if end_date:
            entity_filter["endDate"] = end_date
        extended_filter = []
        detection_resolution_filter = {}
        if direction:
            extended_filter.append(
                {
                    "saasAttrName": f"entityPayload.is{direction}",
                    "saasAttrOp": "is",
                    "saasAttrValue": "true",
                }
            )
        if subject_contains:
            extended_filter.append(
                {"saasAttrName": "entityPayload.subject", "saasAttrOp": "contains", "saasAttrValue": subject_contains}
            )
        elif subject_match:
            extended_filter.append({"saasAttrName": "entityPayload.subject", "saasAttrOp": "is", "saasAttrValue": subject_match})
        if sender_contains:
            extended_filter.append(
                {"saasAttrName": "entityPayload.fromEmail", "saasAttrOp": "contains", "saasAttrValue": sender_contains}
            )
        elif sender_match:
            extended_filter.append({"saasAttrName": "entityPayload.fromEmail", "saasAttrOp": "is", "saasAttrValue": sender_match})
        if domain:
            extended_filter.append({"saasAttrName": "entityPayload.fromDomain", "saasAttrOp": "is", "saasAttrValue": domain})
        if cp_detection:
            detection_resolution_filter["cpDetection"] = cp_detection
        if ms_detection:
            detection_resolution_filter["msDetection"] = ms_detection
        if cp_detection and ms_detection:
            detection_resolution_filter["detectionOp"] = detection_op
        if server_ip:
            extended_filter.append(
                {"saasAttrName": "entityPayload.senderServerIp", "saasAttrOp": "is", "saasAttrValue": server_ip}
            )
        if recipients_contains:
            extended_filter.append(
                {"saasAttrName": "entityPayload.recipients", "saasAttrOp": "contains", "saasAttrValue": recipients_contains}
            )
        elif recipients_match:
            extended_filter.append(
                {"saasAttrName": "entityPayload.recipients", "saasAttrOp": "is", "saasAttrValue": recipients_match}
            )
        if links:
            extended_filter.append({"saasAttrName": "entityPayload.emailLinks", "saasAttrOp": "is", "saasAttrValue": links})
        if message_id:
            extended_filter.append(
                {"saasAttrName": "entityPayload.internetMessageId", "saasAttrOp": "is", "saasAttrValue": message_id}
            )
        if cp_quarantined_state:
            detection_resolution_filter["cpQuarantinedState"] = cp_quarantined_state
        if ms_quarantined_state:
            detection_resolution_filter["msQuarantinedState"] = ms_quarantined_state
        if cp_quarantined_state and ms_quarantined_state:
            detection_resolution_filter["quarantinedStateOp"] = quarantined_state_op
        if name_contains:
            extended_filter.append(
                {"saasAttrName": "entityPayload.fromName", "saasAttrOp": "contains", "saasAttrValue": name_contains}
            )
        elif name_match:
            extended_filter.append({"saasAttrName": "entityPayload.fromName", "saasAttrOp": "is", "saasAttrValue": name_match})
        if client_ip:
            extended_filter.append(
                {"saasAttrName": "entityPayload.senderClientIp", "saasAttrOp": "is", "saasAttrValue": client_ip}
            )
        if attachment_md5:
            extended_filter.append(
                {"saasAttrName": "entityPayload.attachments.MD5", "saasAttrOp": "is", "saasAttrValue": attachment_md5}
            )
        request_data = {
            "entityFilter": entity_filter,
        }
        if extended_filter:
            request_data["entityExtendedFilter"] = extended_filter
        if detection_resolution_filter:
            request_data["entityDetectionResolutionFilter"] = detection_resolution_filter
        payload = {"requestData": request_data}
        print(payload)
        return self.call_api('post', 'search/query', body=payload)

    def event_action(self, event_ids: List[str], action: str, scope: str = None):
        """
        Perform action on the entities associated with a security event

        :param event_ids: List of Event ID
        :param action: Action to perform ('quarantine' or 'restore')
        :param scope: Single scope (mandatory for multi scope app clients)
        :return: Task information
        """
        request_data = {
            'scope': scope,
            'eventIds': event_ids,
            'eventActionName': action
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', 'action/event', body=payload)

    def entity_action(self, entity_ids: List[str], entity_type: str, action: str, restore_decline_reason: str = None):
        """
        Enqueues an action on SaaS entity

        :param entity_ids: List of Entity ID
        :param entity_type: SaaS Entity Type
        :param action: Action to perform ('quarantine' or 'restore')
        :param restore_decline_reason: Reason for declining restore action (used if action is "decline_restore_request")
        :return: Task information
        """
        request_data = {
            'entityIds': entity_ids,
            'entityType': entity_type,
            'entityActionName': action,
        }
        if action == 'decline_restore_request':
            request_data['restoreDeclineReason'] = restore_decline_reason
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', 'action/entity', body=payload)

    def get_task(self, task_id: int, scope: str = None):
        """
        Returns the state of actions enqueued with "entity_action".

        :param task_id: Task ID from "Task Information" (returned by the action endpoints)
        :param scope: Single scope (mandatory for multi scope app clients)
        :return: Updated Task Information
        """
        params = {'scope': scope} if scope else None
        return self.call_api('get', f'task/{task_id}', params=params)

    def send_email(self, entity_id: str, emails: List[str]):
        request_data = {
            'entityId': entity_id,
            'emails': emails,
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', 'soar/notify', body=payload)

    def download_email(self, entity_id: str, original: bool = False, scope: str = None):
        """
        Download email file associated with the entity ID.

        :param entity_id: Email Entity ID
        :param original: Whether to download original email or with modifications
        :param scope: Single scope (mandatory for multi scope app clients)
        """
        params = {
            'scope': scope,
            'original': original
        }
        self.strip_none(params)
        return self.call_api('get', f'download/entity/{entity_id}', params=params)

    def report_mis_classification(self, entities: List[str], classification: str, confident: str):
        """
        Report misclassification for given entities.

        :param entities: List of entity IDs
        :param classification: Classification
        :param confident: Confidence level
        """
        request_data = {
            'entityIds': entities,
            'classification': classification,
            'confident': confident
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', 'report/mis-classification', body=payload)

    def get_sectool_exception(self, sectool: str, exception_type: str, exception_string: str, scope: str = None):
        """
        Returns a single sectool exception.

        :param sectool: Sectool name - avanan_dlp, avanan_url, checkpoint2
        :param exception_type: Exception type
        :param exception_string: Exception string
        :param scope: Single scope (mandatory for multi scope app clients)
        """
        params = {'scope': scope} if scope else None
        return self.call_api(
            'get',
            f'sectool-exceptions/{sectool}/exceptions/{exception_type}/{exception_string}',
            params=params
        )

    def get_sectool_exceptions(self, sectool: str, exception_type: str, exception_data: dict, scope: str = None):
        """
        Returns list of sectool exceptions.

        :param sectool: Sectool name - avanan_dlp, avanan_url, checkpoint2
        :param exception_type: Exception type
        :param exception_data: Exception data for filtering
        :param scope: Single scope (mandatory for multi scope app clients)
        """
        params = {'scope': scope} if scope else None
        self.strip_none(exception_data)
        payload = {
            'requestData': exception_data
        }
        return self.call_api('get', f'sectool-exceptions/{sectool}/exceptions/{exception_type}', params=params, body=payload)

    def create_sectool_exception(self, sectool: str, exc: dict, scopes: List[str] = None):
        """
        Create a sectool exception.

        :param sectool: Sectool name - avanan_dlp, avanan_url, checkpoint2
        :param exc: Exception data
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            **exc
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', f'sectool-exceptions/{sectool}', body=payload)

    def update_sectool_exception(self, sectool: str, exc: dict, scopes: List[str] = None):
        """
        Update a sectool exception.

        :param sectool: Sectool name - avanan_dlp, avanan_url, checkpoint2
        :param exc: Exception data
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            **exc
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('put', f'sectool-exceptions/{sectool}', body=payload)

    def delete_sectool_exception(self, sectool: str, exc: dict, scopes: List[str] = None):
        """
        Delete a sectool exception.

        :param sectool: Sectool name - avanan_dlp, avanan_url, checkpoint2
        :param exc: Exception data
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            **exc
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('delete', f'sectool-exceptions/{sectool}', body=payload)

    def delete_sectool_exceptions(self, sectool: str, exc: dict, scopes: List[str] = None):
        """
        Delete multiple sectool exceptions.

        :param sectool: Sectool name - avanan_dlp, avanan_url, checkpoint2
        :param exc: Exception data
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            **exc
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('delete', f'sectool-exceptions/{sectool}/exceptions', body=payload)

    def get_exceptions(self, exc_type: str, scope: str = None):
        """
        Returns list of exception by the type (whitelist/blacklist).

        :param exc_type: Exception type - whitelist/blacklist
        :param scope: Single scope (mandatory for multi scope app clients)
        """
        params = {'scope': scope} if scope else None
        return self.call_api('get', f'exceptions/{exc_type}', params=params)

    def get_ap_exception(self, exc_type: str, exc_id: str, scope: str = None):
        """
        Returns a single exception by the type (whitelist/blacklist) and ID.

        :param exc_type: Exception type - whitelist/blacklist
        :param exc_id: Exception ID
        :param scope: Single scope (mandatory for multi scope app clients)
        """
        params = {'scope': scope} if scope else None
        return self.call_api('get', f'exceptions/{exc_type}/{exc_id}', params=params)

    def get_ap_exceptions(self, exc_type: str, scope: str = None):
        """
        Returns list of exceptions by the type (whitelist/blacklist).

        :param exc_type: Exception type - whitelist/blacklist
        :param scope: Single scope (mandatory for multi scope app clients)
        """
        params = {'scope': scope} if scope else None
        return self.call_api('get', f'exceptions/{exc_type}', params=params)

    def create_ap_exception(self, exc_type: str, exc: dict, scopes: List[str] = None):
        """
        Create an exception of type (whitelist/blacklist).

        :param exc_type: Exception type - whitelist/blacklist
        :param exc: Exception data
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            **exc
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', f'exceptions/{exc_type}', body=payload)

    def update_ap_exception(self, exc_type: str, exc_id: str, exc: dict, scopes: List[str] = None):
        """
        Returns a single exception by the type (whitelist/blacklist) and ID.

        :param exc_type: Exception type - whitelist/blacklist
        :param exc_id: Exception ID
        :param exc: Exception data
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            **exc
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('put', f'exceptions/{exc_type}/{exc_id}', body=payload)

    def delete_ap_exception(self, exc_type: str, exc_id: str, scopes: List[str] = None):
        """
        Delete a single exception by the type (whitelist/blacklist) and ID.

        :param exc_type: Exception type - whitelist/blacklist
        :param exc_id: Exception ID
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', f'exceptions/{exc_type}/delete/{exc_id}', body=payload)

    def get_anomaly_exceptions(self, scope: str = None):
        """
        Get anomaly exceptions.

        :param scope: Single scope (mandatory for multi scope app clients)
        """
        params = {'scope': scope} if scope else None
        return self.call_api('get', 'sectools/anomaly/exceptions', params=params)

    def create_anomaly_exception(self, exc: dict, added_by: str = None, scopes: List[str] = None):
        """
        Create an anomaly exception.

        :param exc: Exception data
        :param added_by: Name of the user who added the exception
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            'addedBy': added_by,
            'requestJson': exc
        }
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', 'sectools/anomaly/exceptions', body=payload)

    def delete_anomaly_exceptions(self, list_ids: List[str], scopes: List[str] = None):
        """
        Delete anomaly exceptions.

        :param list_ids: List of exception IDs to delete
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            'listIds': list_ids
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('delete', 'sectools/anomaly/exceptions', body=payload)

    def create_ctp_list_item(self, list_item: dict, scopes: List[str] = None):
        """
        Create a CTP list item.

        :param list_item: List item data
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            **list_item
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('post', 'sectools/click_time_protection/exceptions/items', body=payload)

    def get_ctp_list(self, list_id: str, scopes: List[str] = None):
        """
        Get a CTP list.

        :param list_id: List ID
        :param scopes: List of scopes as <farm>:<customer>
        """
        params = {
            'scopes': scopes
        }
        self.strip_none(params)
        return self.call_api('get', f'sectools/click_time_protection/exceptions/{list_id}', params=params)

    def get_ctp_list_item(self, item_id: str, scopes: List[str] = None):
        """
        Get a CTP list item.

        :param item_id: List item ID
        :param scopes: List of scopes as <farm>:<customer>
        """
        params = {
            'scopes': scopes
        }
        self.strip_none(params)
        return self.call_api('get', f'sectools/click_time_protection/exceptions/items/{item_id}', params=params)

    def get_ctp_list_items(self, scopes: List[str] = None):
        """
        Get CTP list items.

        :param scopes: List of scopes as <farm>:<customer>
        """
        params = {
            'scopes': scopes
        }
        self.strip_none(params)
        return self.call_api('get', 'sectools/click_time_protection/exceptions/items', params=params)

    def get_ctp_lists(self, scopes: List[str] = None):
        """
        Get CTP lists.

        :param scopes: List of scopes as <farm>:<customer>
        """
        params = {
            'scopes': scopes
        }
        self.strip_none(params)
        return self.call_api('get', 'sectools/click_time_protection/exceptions', params=params)

    def update_ctp_list_item(self, item_id: str, list_item: dict, scopes: List[str] = None):
        """
        Update a CTP list item.

        :param item_id: List item ID
        :param list_item: List item data
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            **list_item
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('put', f'sectools/click_time_protection/exceptions/items/{item_id}', body=payload)

    def delete_ctp_list_item(self, item_id: str, scopes: List[str] = None):
        """
        Delete a CTP list item.

        :param item_id: List item ID
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('delete', f'sectools/click_time_protection/exceptions/items/{item_id}', body=payload)

    def delete_ctp_list_items(self, list_item_ids: List[str], scopes: List[str] = None):
        """
        Delete multiple CTP list items.

        :param list_item_ids: List of item IDs
        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes,
            'listItemIds': list_item_ids
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('delete', 'sectools/click_time_protection/exceptions/items', body=payload)

    def delete_ctp_lists(self, scopes: List[str] = None):
        """
        Delete all CTP lists.

        :param scopes: List of scopes as <farm>:<customer>
        """
        request_data = {
            'scopes': scopes
        }
        self.strip_none(request_data)
        payload = {
            'requestData': request_data
        }
        return self.call_api('delete', 'sectools/click_time_protection/exceptions', body=payload)


class CloudInfraApiClient(APIBaseClient):

    def __init__(self, host: str, client_id: str, client_secret: str, verify_ssl: bool):
        self.auth_manager = CloudInfraAuthManager(host, client_id, client_secret)
        self.verify_ssl = verify_ssl

    def get_path(self, endpoint: str) -> str:
        return '/'.join(['app', 'hec-api', self.api_version, endpoint])

    def get_request_string(self, endpoint: str, params: dict = None) -> str:
        return ''


class SmartAPIClient(APIBaseClient):

    def __init__(self, host: str, client_id: str, client_secret: str, verify_ssl: bool):
        self.auth_manager = SmartAPIAuthManager(host, client_id, client_secret)
        self.verify_ssl = verify_ssl

    def get_path(self, endpoint: str) -> str:
        return '/'.join([self.api_version, endpoint])

    def get_request_string(self, endpoint: str, params: dict = None) -> str:
        request_string = f'/{self.api_version}/{endpoint}'
        if params:
            request_string += f'?{urlencode(params)}'
        return request_string
