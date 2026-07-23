from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import requests
import base64
import time
import uuid
import jwt
from OpenSSL import crypto

from TIPCommon.filters import filter_old_alerts
from TIPCommon.types import SingleJson
from . import constants
from .datamodels import Alert, Incident
from .exceptions import (
    MicrosoftGraphSecurityFileNotFound,
    MicrosoftGraphSecurityManagerError,
)
from .MicrosoftGraphSecurityParser import MicrosoftGraphSecurityParser


class MicrosoftGraphSecurityManager:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        certificate_path: str,
        certificate_password: str,
        tenant: str,
        verify_ssl: bool = False,
        siemplify=None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.certificate_path = certificate_path
        self.certificate_password = certificate_password
        self.tenant = tenant
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.access_token: str = self.generate_token(
            self.client_id,
            self.client_secret,
            self.certificate_path,
            self.certificate_password,
            self.tenant,
        )
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        self.parser = MicrosoftGraphSecurityParser()
        self.siemplify = siemplify

    def generate_token(
        self,
        client_id: str,
        client_secret: str,
        certificate_path: str,
        certificate_password: str,
        tenant: str,
    ) -> str:
        """
        Request access token
        :param client_id: {string} The Application ID that the registration portal
        :param client_secret: {string} The application secret that you created in the app registration portal for your app.
        :param certificate_path: {string} If authentication based on certificates is used instead of client secret, specify path to the certificate on Siemplify server..
        :param certificate_password: {string} If certificate is password-protected, specify the password to open the certificate file.
        :param tenant: {string} domain name from azure portal
        :return: {string} Access token. The app can use this token in calls to Microsoft Graph.
        """
        if client_secret:
            return self.generate_token_by_client_secret(
                client_id, client_secret, tenant
            )

        return self.generate_token_by_certificate(
            client_id, certificate_path, certificate_password, tenant
        )

    def generate_token_by_client_secret(
        self,
        client_id: str,
        client_secret: str,
        tenant: str
    ) -> str:
        """Request access token by client secret (Valid for 60 min)

        Args:
            client_id (str): The Application ID that the registration portal.
            client_secret (str): The application secret that you created in the app
                registration portal for your app.
            tenant (str): Domain name from azure portal.

        Returns:
            str: Access token. The app can use this token in calls to Microsoft Graph.
        """
        payload = deepcopy(constants.TOKEN_PAYLOAD)
        payload["client_id"] = client_id
        payload["client_secret"] = client_secret
        res = self.session.post(
            constants.ACCESS_TOKEN_URL.format(tenant=tenant), data=payload)
        MicrosoftGraphSecurityManager.validate_response(res)
        return res.json().get("access_token")

    def generate_token_by_certificate(
        self, client_id, certificate_path, certificate_password, tenant
    ):
        """
        Request access token by certificate (Valid for 60 min)
        :param client_id: {string} The Application ID that the registration portal
        :param certificate_path: {string} If authentication based on certificates is used instead of client secret, specify path to the certificate on Siemplify server
        :param certificate_password: {string} If certificate is password-protected, specify the password to open the certificate file
        :param tenant: {string} domain name from azure portal
        :return: {string} Access token. The app can use this token in calls to Microsoft Graph
        """
        thumbprint, private_key = self.get_certificate_thumbprint_and_private_key(
            certificate_path, certificate_password
        )
        jwt_token = self.get_jwt_token(client_id, tenant, thumbprint, private_key)

        params = {
            "grant_type": constants.GRANT_TYPE,
            "scope": constants.SCOPE,
            "client_id": client_id,
            "client_assertion_type": constants.CLIENT_ASSERTION_TYPE,
            "client_assertion": jwt_token,
        }

        response = self.session.post(
            constants.ACCESS_TOKEN_URL.format(tenant=tenant),
            data=params,
        )
        MicrosoftGraphSecurityManager.validate_response(response)
        return response.json().get("access_token")

    def get_certificate_thumbprint_and_private_key(
        self, certificate_path, certificate_password
    ):
        """
        Get thumbprint and private key from certificate
        :param certificate_path: {string} If authentication based on certificates is used instead of client secret, specify path to the certificate on Siemplify server
        :param certificate_password: {string} If certificate is password-protected, specify the password to open the certificate file
        :return: {tuple} The certificate thumbprint and private key
        """
        try:
            with open(certificate_path, "rb") as pfx:
                certificate = crypto.load_pkcs12(pfx.read(), certificate_password)
                private_key_object = certificate.get_privatekey()
                x509_certificate = certificate.get_certificate()
                thumbprint_bytes = x509_certificate.digest("sha1")
                # Remove colons from thumbprint
                thumbprint = thumbprint_bytes.decode("utf-8").replace(":", "")
                private_key = crypto.dump_privatekey(
                    crypto.FILETYPE_PEM, private_key_object
                )

                return thumbprint, private_key
        except Exception:
            raise MicrosoftGraphSecurityFileNotFound("Unable to read certificate file")

    def get_jwt_token(self, client_id, tenant, thumbprint, private_key):
        """
        Get JWT token
        :param client_id: {string} The Application ID that the registration portal
        :param tenant: {string} domain name from azure portal
        :param thumbprint: {string} The certificate thumbprint
        :param private_key: The certificate private key
        :return: {bytes} The JWT token
        """
        # Encode hex to Base64
        encoded_thumbprint = base64.b64encode(bytes.fromhex(thumbprint)).decode("utf-8")
        # Perform base64url-encoding as per RFC7515 Appendix C
        x5t = encoded_thumbprint.replace("=", "").replace("+", "-").replace("/", "_")
        current_timestamp = int(time.time())

        payload = {
            "aud": constants.ACCESS_TOKEN_URL.format(tenant=tenant),
            "exp": current_timestamp + 3600,
            "iss": client_id,
            "jti": str(uuid.uuid1()),
            "nbf": current_timestamp,
            "sub": client_id,
        }

        jwt_token = jwt.encode(
            payload, private_key, algorithm="RS256", headers={"x5t": x5t}
        )
        return jwt_token.decode("utf-8")

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {unicode} Default message to display on error
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                err = response.json().get("error")
                err_msg = err.get("message") if "message" in err else err
                raise MicrosoftGraphSecurityManagerError(
                    f"{error_msg}: {err_msg}"
                ) from error

            except (ValueError, KeyError) as exc:
                raise MicrosoftGraphSecurityManagerError(
                    f"{error_msg}: {error} {response.content}"
                ) from exc

    def get_alert_details(self, alert_id: str) -> dict:
        """
        Retrieve the properties and relationships of an alert object.
        :param alert_id: {string} alert id
        :return: {Alert} The alert
        """
        # There can be few alerts with the same title, therefore the search is by id
        response = self.session.get(f"{constants.GET_ALERT_URL}/{alert_id}")
        self.validate_response(response, f"Unable to get alert {alert_id}")
        return self.parser.build_siemplify_alert_obj(response.json())

    @staticmethod
    def _build_api_parameters(
        provider_list: list = None,
        severity_list: list = None,
        status_list: list = None,
        start_time: datetime = None,
        asc: bool = True,
        filter_dict: dict = None,
    ) -> dict:
        """
        Build the parameters dict for API call
        :param provider_list: {list} List of provider names to filter with
        :param severity_list: {list} List of severities to filter with
        :param status_list: {list} List of statuses to filter with
        :param start_time: {str} Start time to filter with
        :param asc: {bool} Whether to return the results ascending or descending
        :param filter_dict: {dict} The filter params {key: , logic: , value: ,}
        :return: {dict} The params dict
        """
        filter_params = []

        if provider_list:
            provider_filter_group = " or ".join(
                map(lambda x: f"(vendorInformation/provider eq '{x}')", provider_list)
            )
            filter_params.append(f"({provider_filter_group})")

        if severity_list:
            severity_filter_group = " or ".join(
                map(lambda x: f"(severity eq '{x}')", severity_list)
            )
            filter_params.append(f"({severity_filter_group})")

        if status_list:
            status_filter_group = " or ".join(
                map(lambda x: f"(status eq '{x}')", status_list)
            )
            filter_params.append(f"({status_filter_group})")

        if start_time:
            filter_params.append(
                f"createdDateTime ge {start_time.strftime(constants.TIME_FORMAT)}"
            )

        if filter_dict is not None:
            if filter_dict["logic"] == "Equal":
                filter_params.append(
                    f"{filter_dict['key']} eq '{filter_dict['value']}'"
                )
            elif filter_dict["logic"] == "Contains":
                filter_params.append(
                    f"contains({filter_dict['key']}, '{filter_dict['value']}')"
                )

        # Apply filtering in oData format
        params = {
            "$filter": " and ".join(filter_params) if filter_params else None,
            "$orderby": f"createdDateTime {'asc' if asc else 'desc'}",
        }

        return params

    def update_alert(
        self,
        alert_id: str,
        assigned_to: str = None,
        closed_date_time: datetime = None,
        comments: list = None,
        feedback: str = None,
        status: str = None,
        tags: list = None,
    ):
        """
        Update an editable alert property within any integrated solution to keep alert status and assignments in sync across solutions.
        :param alert_id: {string} alert id
        :param assigned_to: {string} Name of the analyst the alert is assigned to for triage, investigation, or remediation.
        :param closed_date_time: {DateTime} Time at which the alert was closed. using iso format, always in UTC time. ex.'2014-01-01T00:00:00Z'
        :param comments: {list} Analyst comments on the alert
        :param feedback: {string} Analyst feedback on the alert. Possible values are: unknown, truePositive, falsePositive, benignPositive.
        :param status: {string} Alert lifecycle status (stage). Possible values are: unknown, newAlert, inProgress, resolved.
        :param tags: {list} User-definable labels that can be applied to an alert and can serve as filter conditions (for example, "HVA", "SAW).
        :return: {Alert} The updated alert
        """
        # In the request body, supply a JSON representation of the values for relevant fields that should be updated.
        # The body must contain the vendorInformation property with valid provider and vendor fields.
        # For best performance, don't include existing values that haven't changed.
        # Check which fields the user want to update.
        alert_updated_json = {}

        if assigned_to:
            alert_updated_json["assignedTo"] = assigned_to
        if closed_date_time:
            alert_updated_json["closedDateTime"] = closed_date_time
        if comments:
            alert_updated_json["comments"] = comments
        if feedback:
            if feedback in constants.FEEDBACK_VALUES:
                alert_updated_json["feedback"] = feedback
        if status:
            if status in constants.STATUS_VALUES:
                alert_updated_json["status"] = status
        if tags:
            alert_updated_json["tags"] = tags

        # The body must contain the vendorInformation property with valid provider and vendor fields.
        # Get this details from the alert
        alert_details = self.get_alert_details(alert_id)
        alert_updated_json["vendorInformation"] = alert_details.vendorInformation

        update_alert_headers = deepcopy(self.session.headers)
        update_alert_headers.update(constants.UPDATE_ALERT_HEADER)
        response = self.session.patch(
            f"{constants.GET_ALERT_URL}/{alert_id}",
            json=alert_updated_json,
            headers=update_alert_headers,
        )

        self.validate_response(response)
        return self.parser.build_siemplify_alert_obj(response.json())

    def list_alerts(
        self,
        provider_list=None,
        severity_list=None,
        status_list=None,
        start_time=None,
        max_alerts=None,
        asc=True,
        existing_ids=None,
        filter_dict=None,
    ):
        """
        Retrieve a list of alert objects.
        :param provider_list: {list} List of provider names to filter with
        :param severity_list: {list} List of severities to filter with
        :param status_list: {list} List of statuses to filter with
        :param start_time: {str} Start time to filter with
        :param max_alerts: {int} Max amount of alerts to return
        :param asc: {bool} Whether to return the results ascending or descending
        :param existing_ids: {list} The list of existing ids
        :param filter_dict: {dict} The filter params {key: , logic: , value: ,}
        :return: {[Alert]} List of found alerts
        """
        if existing_ids is None:
            existing_ids = []

        api_parameters = self._build_api_parameters(
            provider_list, severity_list, status_list, start_time, asc, filter_dict
        )

        raw_alerts = self._paginate_results(
            url=constants.GET_ALERT_URL, params=api_parameters, limit=max_alerts
        )
        alerts = [self.parser.build_siemplify_alert_obj(alert) for alert in raw_alerts]

        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alerts,
            existing_ids=existing_ids,
            id_key=constants.ALERT_ID_FIELD,
        )
        return filtered_alerts[:max_alerts] if max_alerts else filtered_alerts

    def list_incidents(
        self,
        filter_dict: SingleJson,
        max_incidents: int | None = None,
    ) -> list[Incident]:
        """Retrieves a list of incidents based on the specified filter criteria and
        maximum number of incidents.

        Args:
            filter_dict (SingleJson): A dict containing the filtering parameters to
                apply when retrieving incidents.
            max_incidents (int | None): The maximum number of incidents to retrieve.

        Returns:
            list[Incident]: A list of Incident objects created from the raw incident
                data returned by the API.
        """
        api_parameters = self._build_api_parameters(filter_dict=filter_dict)
        raw_incidents = self._paginate_results(
            url=constants.GET_INCIDENTS_URL,
            params=api_parameters,
            limit=max_incidents,
        )

        return [
            self.parser.build_siemplify_incident_obj(incident_data)
            for incident_data in raw_incidents
        ]

    def get_incident(self, incident_id: str) -> Incident:
        """Get an incident based on Incident ID.

        Args:
            incident_id (str): Incident ID.

        Returns:
            Incident: Incident object.
        """
        response = self.session.get(
            constants.GET_INCIDENT_URL.format(incident_id=incident_id)
        )
        self.validate_response(response)
        return self.parser.build_siemplify_incident_obj(response.json())

    def _paginate_results(
        self,
        url: str,
        params: dict | None = None,
        limit: int | None = None,
    ) -> list[SingleJson]:
        """Paginates through API results.

        Args:
            url (str): URL for the request.
            params (dict | None): Parameters for the request.
            limit (int | None): limit for the number of results to fetch.

        Returns:
            list[SingleJson]: List of parsed results.
        """
        results = []
        while url:
            if limit and len(results) >= limit:
                break

            response = self.session.get(url, params=params)
            self.validate_response(response)

            current_items = response.json().get("value", [])
            results.extend(current_items)

            url = response.json().get("@odata.nextLink")
            params = {}

        return results[:limit] if limit else results

    def list_users(self):
        """
        Retrieve a list of users objects.
        :return: {list} of alerts {dicts}
        """
        res = self.session.get(constants.GET_USERS_URL)
        self.validate_response(res)
        return res.json().get("value", [])

    def kill_user_session(self, user_id):
        """
        Kill a user session by the userPrincipalName or the user id
        :param user_id: {str} The identifier of the user to kill
        :return: {bool} True if successful, exception otherwise
        """
        res = self.session.post(constants.KILL_USER_URL.format(user_id))
        self.validate_response(res)
        return True

    def add_comment_to_alert(self, alert_id: str, comment: str) -> None:
        """Adds comment to the alert.

        Args:
            alert_id (str): Alert ID
            comment (str): Comment to be added in the alert.
        """
        data = {
            "@odata.type": "microsoft.graph.security.alertComment",
            "comment": comment,
        }

        response = self.session.post(
            constants.ADD_ALERT_COMMENT.format(alert_id),
            json=data
        )
        self.validate_response(response)


class MicrosoftGraphSecurityManagerV2(MicrosoftGraphSecurityManager):

    def get_alert_details(self, alert_id: str) -> Alert:
        """Gets alerts details.

        Args:
            alert_id (str): Alert ID.

        Returns:
            Alert: Alert details.
        """
        response = self.session.get(f"{constants.GET_ALERT_V2_URL}/{alert_id}")
        self.validate_response(response, f"Unable to get alert {alert_id}")

        return self.parser.build_siemplify_alert_obj(response.json())

    def update_alert(
        self,
        alert_id: str,
        status: str,
        assigned_to: str,
        comments: str,
        feedback: str,
    ) -> Alert:
        """Updates an alert in the v2 API.

        Args:
            alert_id (str): The ID of the alert.
            status (str): The new status of the alert.
            assigned_to (str): The user to assign the alert to.
            comment (str): The comment to add to the alert.
            feedback (str): The classification to add to the alert.

        Returns:
            Alert: The response from the API.
        """
        alert_updated_json = {}
        if assigned_to:
            alert_updated_json["assignedTo"] = assigned_to
        if status and status in constants.STATUS_VALUES:
            if status == "newAlert":
                status = "new"
            alert_updated_json["status"] = status
        if comments:
            self.add_comment_to_alert(alert_id, comments)
        if feedback and feedback in constants.CLASSIFICATION_VALUES:
            alert_updated_json["classification"] = feedback

        update_alert_headers = deepcopy(self.session.headers)
        update_alert_headers.update(constants.UPDATE_ALERT_HEADER)
        response = self.session.patch(
            f"{constants.GET_ALERT_V2_URL}/{alert_id}",
            json=alert_updated_json,
            headers=update_alert_headers,
        )

        self.validate_response(response)
        return self.parser.build_siemplify_alert_obj(response.json())

    def list_alerts(
        self,
        provider_list: list[str] | None = None,
        severity_list: list[str] | None = None,
        status_list: list[str] | None = None,
        start_time:datetime | None = None,
        max_alerts:int | None = None,
        asc: bool = True,
        existing_ids: list[str] | None = None,
        filter_dict: SingleJson | None = None,
    ) -> Alert:
        """List alerts

        Args:
            provider_list (list[str] | None): Provider's list.
            severity_list (list[str] | None): Severity list.
            status_list (list[str] | None): Status list.
            start_time (datetime | None): Start time to filter alerts.
            max_alerts (int | None): Max alerts to fetch.
            asc (bool): Ascending order for alerts.
            existing_ids (list[str] | None): List of existing alert ids.
            filter_dict (SingleJson | None): Dict to filter alerts.

        Returns:
            Alert: Alert object.
        """
        if existing_ids is None:
            existing_ids = []

        api_parameters = self._build_api_parameters_v2(
            provider_list=provider_list,
            severity_list=severity_list,
            status_list=status_list,
            start_time=start_time,
            asc=asc,
            filter_dict=filter_dict,
        )
        raw_alerts = self._paginate_results(
            url=constants.GET_ALERT_V2_URL,
            params=api_parameters,
            limit=max_alerts,
        )
        alerts = [self.parser.build_siemplify_alert_obj(alert) for alert in raw_alerts]

        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alerts,
            existing_ids=existing_ids,
            id_key=constants.ALERT_ID_FIELD,
        )
        return filtered_alerts[:max_alerts] if max_alerts else filtered_alerts

    def _build_api_parameters_v2(
        self,
        provider_list: list[str] | None = None,
        severity_list: list[str] | None= None,
        status_list: list[str] | None = None,
        start_time: datetime | None = None,
        asc: bool = True,
        filter_dict: SingleJson | None = None,
    ) -> SingleJson:
        """Build the parameters dict for API call.

        Args:
            provider_list (list[str] | None): Provider's list.
            severity_list (list[str] | None): Severity list.
            status_list (list[str] | None): Status list.
            start_time (datetime | None): Start time to filter alerts.
            asc (bool): _description_. Ascending order for alerts.
            filter_dict (SingleJson | None): Dict to filter alerts.

        Returns:
            SingleJson: Dict with the parameters.
        """
        filter_params = []
        if provider_list:
            provider_filter_group = " or ".join(
                map(lambda x: f"(serviceSource eq '{x}')", provider_list)
            )
            filter_params.append(f"({provider_filter_group})")

        if severity_list:
            severity_filter_group = " or ".join(
                map(lambda x: f"(severity eq '{x}')", severity_list)
            )
            filter_params.append(f"({severity_filter_group})")

        if status_list:
            status_filter_group = " or ".join(
                map(lambda x: f"(status eq '{x}')", status_list)
            )
            filter_params.append(f"({status_filter_group})")

        if start_time:
            filter_params.append(
                f"createdDateTime ge {start_time.strftime(constants.TIME_FORMAT)}"
            )

        if filter_dict is not None:
            if filter_dict["logic"] == "Equal":
                filter_params.append(
                    f"{filter_dict['key']} eq '{filter_dict['value']}'"
                )
            elif filter_dict["logic"] == "Contains":
                filter_params.append(
                    f"contains({filter_dict['key']}, '{filter_dict['value']}')"
                )

        params = {
            "$filter": " and ".join(filter_params) if filter_params else None,
            "$orderby": f"createdDateTime {'asc' if asc else 'desc'}",
        }

        return params
