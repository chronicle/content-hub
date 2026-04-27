from __future__ import annotations
from typing import List, Optional

import json
import requests

from TIPCommon.filters import filter_old_alerts

from .AzureSecurityCenterParser import AzureSecurtyCenterParser
from . import consts
from . import datamodels
from .exceptions import (
    AzureSecurityCenterManagerError,
    AzureSecurityCenterAlertUpdateException,
)


class AzureSecurityCenterManager:
    """
    Azure Security Center Manager
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        tenant_id: str,
        subscription_id: str = None,
        verify_ssl: Optional[bool] = False,
        siemplify=None,
        refresh_token=None,
    ):
        """
        The method is used to init an object of Manager class
        :param client_id: {str} Client ID of the Microsoft Azure application.
        :param client_secret: {str} Client Secret of the Microsoft Azure application.
        :param username: {str} Username of the Microsoft Azure account.
        :param password: {str} Password of the Microsoft Azure account.
        :param tenant_id: {str} Tenant ID of the Microsoft Azure application.
        :param subscription_id: {str} Subscription ID of the Microsoft Azure application
        :param siemplify: {ConnectorExecutor} connector executor instance
        :param refresh_token: {str} Refresh token for the OAuth authorization.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.tenant_id = tenant_id
        self.subscription_id = subscription_id
        self.siemplify = siemplify

        self.parser = AzureSecurtyCenterParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers.update({"SdkVersion": "postman-graph/v1.0"})

        if refresh_token:
            self.auth_token = self.get_access_token(refresh_token)
        elif username and password:
            self.auth_token = self._get_auth_token()
        else:
            raise AzureSecurityCenterManagerError(
                "Please provide necessary parameters for either Basic or "
                "Oauth authentication"
            )

        self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

    def get_access_token(self, refresh_token):
        """
        Obtain the access token
        :param refresh_token: {str} The current refresh token
        :return: {str} The new access token
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        response = self.session.post(
            consts.OAUTH_URL.format(tenant_id=self.tenant_id), data=data
        )
        self.validate_access_token_response(response, "Unable to obtain access token")
        self.new_refresh_token = response.json()["refresh_token"]
        return response.json()["access_token"]

    @staticmethod
    def obtain_refresh_token(
        client_id, client_secret, redirect_uri, code, tenant_id, verify_ssl
    ):
        """
        Obtain a refresh token
        :param client_id: {str} The client id to authenticate with
        :param client_secret: {str} The secret of the given client id
        :param redirect_uri: {str} The redirect uri that matched the given client
        :param code: {str] The generated code from the authorizing step
        :param tenant_id: {str} Tenant ID of the Microsoft Azure application.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the server is valid.
        :return: {str} The new refresh token
        """
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        response = requests.post(
            consts.OAUTH_URL.format(tenant_id=tenant_id), data=data, verify=verify_ssl
        )
        AzureSecurityCenterManager.validate_access_token_response(
            response, error_msg="Unable to obtain refresh token"
        )
        return response.json()

    @staticmethod
    def validate_access_token_response(response, error_msg="An error occurred"):
        """
        Validate the access token response
        :param response: {requests.Response} The response
        :param error_msg: {str} The error message to display on failure
        """
        try:
            response.raise_for_status()

            if response.status_code != 200:
                raise AzureSecurityCenterManagerError(
                    f"{error_msg}: {response.content}"
                )
        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise AzureSecurityCenterManagerError(
                    f"{error_msg}: {error} - {error.response.text}"
                )

            raise AzureSecurityCenterManagerError(
                f"{error_msg}: {response.json().get('error_description')} status code: {response.status_code}"
            )

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate Azure Security Center response
        :param response: the response from a request
        :param error_msg: {str} error message to display
        :return:
            raise AzureSecurityCenterManagerError exceptions
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                json_data = response.json()
                if isinstance(json_data, dict):
                    error_description = (
                        json_data.get("error_description")
                        or json_data.get("error", {}).get("message")
                    )
                else:
                    error_description = str(json_data)

            except (ValueError, json.JSONDecodeError):
                error_description = response.text

            raise AzureSecurityCenterManagerError(
                f"{error_msg}: {error_description} "
                f"(status code: {response.status_code})"
            ) from error

    def _get_full_url(self, url_key, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return consts.ENDPOINTS[url_key].format(**kwargs)

    def _get_auth_token(self, scope=consts.MICROSOFT_SECURITY_CENTER_SCOPE):
        """
        Retrieves Bearer auth token for the manager. By default an auth token for Azure Security Center is returned
        :param scope: {str} Authentication scope. For example https://management.azure.com/.default or https://graph.microsoft.com/.default
        :return: {str} authentication token
        """
        request_url = self._get_full_url(
            url_key="get-auth-token", tenant_id=self.tenant_id
        )
        grant_type = (
            "password"
            if scope == consts.MICROSOFT_SECURITY_CENTER_SCOPE
            else "client_credentials"
        )
        payload = {
            "grant_type": grant_type,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope,
        }

        if scope == consts.MICROSOFT_SECURITY_CENTER_SCOPE:
            payload["userName"] = self.username
            payload["password"] = self.password

        response = self.session.post(url=request_url, data=payload)
        self.validate_response(
            response,
            error_msg="Failed to get authentication token from Azure Security Center",
        )
        return response.json().get("access_token", "")

    def test_connectivity(self):
        """
        Test Connectivity with Azure Security Center
        :return: raise AzureSecurityCenterManagerError if failed to test connectivity with Azure Security Center
        """
        request_url = self._get_full_url(url_key="ping")
        params = {"api-version": "2015-06-01-preview"}
        response = self.session.get(url=request_url, params=params)
        self.validate_response(
            response, error_msg="Failed to connect to Azure Security Center"
        )

    def get_regulatory_standards(
        self, state_filters=None, limit: Optional[int] = None
    ) -> [datamodels.RegulatoryStandard]:
        """
        Returns list of available regulatory standards in Microsoft Azure Security Center. If state filters
        are not specified, all regulatory standards will be returned
        :param limit: {int} Max limit of standards to return
        :param state_filters: {[str]} List of state filters of standards to return.  Must be all lowercased!
        :return: {[datamodels.RegulatoryStandard]} List of RegulatoryStandard datamodels
        """
        request_url = self._get_full_url(
            url_key="list-regulatory-standards", subscription_id=self.subscription_id
        )
        params = {"api-version": "2019-01-01-preview"}
        response = self.session.get(url=request_url, params=params)
        self.validate_response(response, error_msg="Failed to get regulatory standards")
        fetched_standards = [
            self.parser.build_regulatory_standard_obj(value)
            for value in response.json().get("value", [])
        ]

        if not state_filters:
            return fetched_standards[:limit] if limit is not None else fetched_standards

        filtered_standards = [
            regulatory_standard
            for regulatory_standard in fetched_standards
            if regulatory_standard.state.lower() in state_filters
        ]

        return filtered_standards[:limit] if limit is not None else filtered_standards

    def get_regulatory_standard_controls(
        self, state_filters=None, standard_name=None, limit: Optional[int] = None
    ) -> [datamodels.RegulatoryStandard]:
        """
        Returns list of standards in Microsoft Azure Security Center.
        :param limit: {int} Max limit of standards to return
        :param state_filters: {[str]} List of state filters of standards to return. Must be all lowercased!
        :param standard_name: {str} Standard name for which to retrieve details
        :return: {[datamodels.RegulatoryStandard]} List of RegulatoryStandard datamodels.
        """
        request_url = self._get_full_url(
            url_key="list-regulatory-standard-controls",
            subscription_id=self.subscription_id,
            standard_name=standard_name,
        )
        params = {"api-version": "2019-01-01-preview"}
        response = self.session.get(url=request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get regulatory standard controls for standard name {standard_name}",
        )
        fetched_standards = [
            self.parser.build_regulatory_control_obj(value, standard_name=standard_name)
            for value in response.json().get("value", [])
        ]

        if not state_filters:
            return fetched_standards[:limit] if limit is not None else fetched_standards

        filtered_standards = [
            regulatory_standard
            for regulatory_standard in fetched_standards
            if regulatory_standard.state.lower() in state_filters
        ]

        return filtered_standards[:limit] if limit is not None else filtered_standards

    def update_alert_status(self, alert_id: str, location: str, alert_status: str):
        """
        Update status of the alert in Microsoft Azure Security Center
        :param alert_id: {str} the id of the alert to update the status to
        :param location: {str} the location of the alert
        :param alert_status: {str} the status of the alert
        :return: raise AzureSecurityCenterManagerError exception if failed to validate response
                 raise AzureSecurityCenterAlertUpdateException exceptions if failed to update alert
        """
        request_url = self._get_full_url(
            url_key="update-alert-status",
            subscription_id=self.subscription_id,
            location=location,
            alert_id=alert_id,
            status=alert_status,
        )
        params = {"api-version": "2020-01-01"}

        response = self.session.post(url=request_url, params=params)
        try:
            res = response.json()
            err_msg = res.get("error", {}).get("message")
            if err_msg:
                raise AzureSecurityCenterAlertUpdateException(err_msg)
        except AzureSecurityCenterAlertUpdateException as e:
            raise e
        except Exception:
            pass

        self.validate_response(
            response,
            error_msg=f"Failed to update alert with id {alert_id} to status {alert_status}",
        )

    def get_alert_ids(
        self,
        severities: List[str],
        start_time: str,
        existing_ids: List[str],
        categories: List[str],
        whitelist_as_blacklist: bool,
        limit: int,
    ):
        """
        Get alerts from Microsoft Graph. Filter already existing alert ids, alert categories behaves as a whitelist for the alerts.
        :param severities: {[str]} list of severities. For example 'high' or 'low'
        :param start_time: {str} time the alerts will be fetched from. In format '2020-11-30T10:09:28Z'
        :param existing_ids: {[str]} list of existing alert ids to filter
        :param categories: {[str]} list of categories the alerts will have.
        :param whitelist_as_blacklist: {bool} True if alerts should be equal to categories. False if alerts should not be equal to
        categories
        :param limit: {int} max filtered alerts to return
        :return: {[datamodels.GraphAlert]} list of filtered Graph Alert data models.
        """
        request_url = self._get_full_url(url_key="get-alert-ids")

        query = """vendorInformation/provider eq 'ASC' and createdDateTime ge {create_from_time} and ({severities}) and 
        azureSubscriptionId eq '{subscription_id}'""".format(
            create_from_time=start_time,
            severities=" or ".join(
                f"severity eq '{severity}'" for severity in severities
            ),
            subscription_id=self.subscription_id,
        )

        if categories:
            operator = "ne" if whitelist_as_blacklist else "eq"
            query += " and ({categories})".format(
                categories=" or ".join(
                    f"category {operator} '{category}'" for category in categories
                )
            )

        params = {
            "$filter": query,
            "$orderby": "createdDateTime asc",
            "$select": "id,sourceMaterials,createdDateTime,category",
            "$top": consts.PAGE_SIZE,
        }

        # Authenticate with Graph
        graph_token = self._get_auth_token(scope=consts.MICROSOFT_GRAPH_SCOPE)
        self.session.headers.update({"Authorization": f"Bearer {graph_token}"})

        response = self.session.get(url=request_url, params=params)

        self.validate_response(response, error_msg="Failed to get alerts ids")
        results = self.parser.extract_values_from_graph_alert_raw_data(response.json())
        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=results,
            existing_ids=existing_ids,
            id_key=consts.ALERT_ID_KEY,
        )

        while True:
            if len(filtered_alerts) >= limit:
                break
            if not response.json().get("@odata.nextLink"):
                break

            self.siemplify.LOGGER.info("Fetching more results..")
            response = self.session.get(url=response.json().get("@odata.nextLink"))
            self.validate_response(response, error_msg="Failed to fetch more alerts")
            results = self.parser.extract_values_from_graph_alert_raw_data(
                response.json()
            )
            if not results:
                self.siemplify.LOGGER.info("Failed to fetch more alert results")
                break
            filtered_alerts.extend(
                filter_old_alerts(
                    siemplify=self.siemplify,
                    alerts=results,
                    existing_ids=existing_ids,
                    id_key=consts.ALERT_ID_KEY,
                )
            )

        # Update back auth token to Azure Security Center
        self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
        return filtered_alerts[:limit] if limit is not None else filtered_alerts

    def get_alert_details(self, location: str, alert_id: str):
        """
        Get alert details from Azure Security Center
        :param location: {str} The location of the alert
        :param alert_id: {str} alert's id to get details from
        :return: {datamodels.AzureAlert or datamodels.AzureIncidentAlert} return Azure Alert or Azure Incident Alert datamodel,
        if the alert is an incident
        """
        request_url = self._get_full_url(
            url_key="get-alert-details",
            subscription_id=self.subscription_id,
            location=location,
            alert_id=alert_id,
        )

        params = {"api-version": "2020-01-01"}

        response = self.session.get(url=request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get detailed information for alert {alert_id}",
        )
        return self.parser.build_azure_alert_obj(
            raw_data=response.json(), alert_location=location
        )

    def get_regulatory_compliance_standards(self, subscription_id):
        """
        Get regulatory compliance standards
        Args:
            subscription_id (str): Subscription ID
        Returns:
            None
        """
        url = self._get_full_url(
            url_key="get-regulatory-compliance-standards",
            subscription_id=subscription_id,
        )
        params = {"api-version": "2019-01-01"}
        response = self.session.get(url=url, params=params)
        self.validate_response(response)
