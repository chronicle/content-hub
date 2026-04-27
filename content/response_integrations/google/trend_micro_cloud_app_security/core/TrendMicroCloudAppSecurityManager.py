from __future__ import annotations
import requests
import json
from .TrendMicroCloudAppSecurityParser import TrendMicroCloudAppSecurityParser
from .TrendMicroCloudAppSecurityExceptions import (
    TrendMicroCloudAppSecurityException,
    APIRateError,
)
from .constants import (
    PING_QUERY,
    ADD_ENTITIES_TO_BLOCKLIST_QUERY,
    GET_EMAILS,
    MITIGATE_EMAILS_QUERY,
    MAX_DAYS_BACKWARDS,
    MITIGATE_ACCOUNT_SERVICE,
    MITIGATE_ACCOUNT_PROVIDER,
    MITIGATE_ACCOUNTS_QUERY,
    FETCH_MITIGATION_RESULTS_QUERY,
)
from soar_sdk.SiemplifyDataModel import EntityTypes


class TrendMicroCloudAppSecurityManager:
    def __init__(
        self, api_root=None, api_key=None, verify_ssl=False, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the TrendMicroCloudAppSecurity
        :param api_key: API Key of the TrendMicroCloudAppSecurity instance.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the TrendMicroCloudAppSecurity server is valid.
        :param siemplify_logger: Siemplify logger.
        """

        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_key = api_key
        self.siemplify_logger = siemplify_logger

        self.parser = TrendMicroCloudAppSecurityParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            if response.status_code == 429:
                raise APIRateError("Maximum allowed requests exceeded")
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise TrendMicroCloudAppSecurityException(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise TrendMicroCloudAppSecurityException(
                f"{error_msg}: {response.json().get('message')} {json.dumps(response.json())}"
            )

    def test_connectivity(self):
        """
        Test integration connectivity.
        """
        result = self.session.get(PING_QUERY.format(self.api_root))
        # Verify result.
        self.validate_response(result)

    def get_blocked_entities(self):
        """
        Function to get all blocked entities
        :return: {BlockedEntitiesObject} Siemplify Object that contains already blocked entities
        """
        result = self.session.get(ADD_ENTITIES_TO_BLOCKLIST_QUERY.format(self.api_root))
        self.validate_response(result)

        return self.parser.build_siemplify_blocked_entities_object(result.json())

    def add_entities_to_blocklist(self, entity_type, entity_to_remove):
        """
        Function that blocks given entities
        :param entity_type: {str} Entity Type URL/USER/FILEHASH
        :param entity_to_remove: {str} The entity that should be removed
        """

        payload = {"action_type": "create", "rules": {}}

        if entity_type == EntityTypes.FILEHASH:
            payload["rules"]["filehashes"] = [entity_to_remove]

        if entity_type == EntityTypes.USER:
            payload["rules"]["senders"] = [entity_to_remove]

        if entity_type == EntityTypes.URL:
            payload["rules"]["urls"] = [entity_to_remove]

        result = self.session.post(
            ADD_ENTITIES_TO_BLOCKLIST_QUERY.format(self.api_root), json=payload
        )
        self.validate_response(result)

    def search_emails(
        self,
        max_emails_to_return,
        max_days_back,
        mailbox=None,
        file_sha1=None,
        file_sha256=None,
        file_name=None,
        url=None,
        subject=None,
        source_ip=None,
    ):
        """
        Function that fetches the emails for an entity
        :param max_emails_to_return: {int} Max number of Emails to return
        :param max_days_back: {int} Max days backwards
        :param mailbox: {str} Mailbox to get emails from
        :param file_sha1: {str} SHA1 Hash to get emails for
        :param file_sha256: {str} SHA256 Hash to get emails for
        :param file_name: {str} File name to get emails for
        :param url: {str} URL to get emails for
        :param subject: {str} Email Subject to get emails for
        :param source_ip: {str} Source IP Address to get emails for
        :return: {List} List of Siemplify Email Objects
        """

        params = {"limit": max_emails_to_return, "lastndays": max_days_back}

        if mailbox:
            params["mailbox"] = mailbox
        if file_sha1:
            params["file_sha1"] = file_sha1
        if file_sha256:
            params["file_sha256"] = file_sha256
        if file_name:
            params["file_name"] = file_name
        if url:
            params["url"] = url
        if source_ip:
            params["source_ip"] = source_ip
        if subject:
            params["subject"] = f'"{subject}"'

        result = self.session.get(GET_EMAILS.format(self.api_root), params=params)
        self.validate_response(result)
        return self.parser.build_siemplify_email_object(result.json())

    def get_email_details(self, message_id):
        """
        Funtion that gets details about an email
        :param message_id: {str} Message ID
        :return: {EmailObject} Siemplify Email Object
        """
        params = {"message_id": message_id, "lastndays": MAX_DAYS_BACKWARDS}

        result = self.session.get(GET_EMAILS.format(self.api_root), params=params)
        self.validate_response(result)
        return self.parser.build_siemplify_email_object(result.json())

    def mitigate_email(
        self,
        action_type,
        service,
        account_provider,
        mailbox,
        mail_message_id,
        mail_unique_id,
        mail_message_delivery_time,
    ):
        """
        Function to mitigate email with given criteria
        :param action_type: {str} Action Type - Quarantine/Delete
        :param service: {str} Service Type - Exchange/Gmail
        :param account_provider: {str} Account Provider
        :param mailbox: {str} Mailbox for which the email should be mitigated
        :param mail_message_id: {str} Mail Message ID
        :param mail_unique_id: {str} Mail Unique ID
        :param mail_message_delivery_time: {str} Mail Message Delivery Time
        """

        payload = [
            {
                "action_type": action_type,
                "service": service,
                "account_provider": account_provider,
                "mailbox": mailbox,
                "mail_message_id": mail_message_id,
                "mail_unique_id": mail_unique_id,
                "mail_message_delivery_time": mail_message_delivery_time,
            }
        ]

        result = self.session.post(
            MITIGATE_EMAILS_QUERY.format(self.api_root), json=payload
        )
        self.validate_response(result)

    def mitigate_account(self, action_type, email_addresses):
        """
        Function to mitigate account with given criteria
        :param action_type: {str} Action Type - ACCOUNT_RESET_PASSWORD/ACCOUNT_ENABLE_MFA/ACCOUNT_RESET_PASSWORD/ACCOUNT_REVOKE_SIGNIN_SESSIONS
        :param email_addresses: {str} Emails to mitigate
        :return {MitigationStatus}: Mitigation status object
        """
        payload = []
        for email in email_addresses:
            email_payload = {
                "action_type": action_type,
                "service": MITIGATE_ACCOUNT_SERVICE,
                "account_provider": MITIGATE_ACCOUNT_PROVIDER,
                "account_user_email": email,
            }
            payload.append(email_payload)

        result = self.session.post(
            MITIGATE_ACCOUNTS_QUERY.format(self.api_root), json=payload
        )
        self.validate_response(result)
        return self.parser.build_siemplify_mitigation_status_object(result.json())

    def fetch_mitigation_results(self, batch_id):
        """
        Function that gets the mitigation results
        :param batch_id: {str} Batch ID to check results for
        :return {MitigationResults}: Mitigation results object
        """
        result = self.session.get(
            FETCH_MITIGATION_RESULTS_QUERY.format(self.api_root, batch_id)
        )
        self.validate_response(result)
        return self.parser.build_siemplify_mitigation_results_object(result.json())
