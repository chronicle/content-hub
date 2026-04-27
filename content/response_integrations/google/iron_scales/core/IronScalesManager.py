from __future__ import annotations
from .IronScalesParser import IronScalesParser
import requests
from urllib.parse import urljoin
from .UtilsManager import validate_response

from .IronScalesConstants import (
    ENDPOINTS,
    HEADERS,
    SCOPES_LIST_COMPANY,
    SCOPES_LIST_PARTNER,
    DEFAULT_PAGE_QTY,
)


class IronScalesManager:

    def __init__(
        self,
        api_root,
        api_token,
        company_id,
        is_partner,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the IronScales instance.
        :param api_token: API token of IronScales.
        :param company_id: Specify the company ID to use in IronScales.
        :param is_partner: Specify whether Company ID from above is a partner ID as well.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the IronScales server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.api_token = api_token
        self.company_id = company_id
        self.is_partner = is_partner
        self.siemplify_logger = siemplify_logger
        self.parser = IronScalesParser()
        self.session = requests.session()
        self.session.headers = HEADERS
        self.session.headers.update(
            {"Authorization": f"Bearer {self.obtain_jwt_token()}"}
        )
        self.session.verify = verify_ssl

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def obtain_jwt_token(self):
        """
        Obtain IronScales authentication security token.
        :return: {str} token
        """
        request_url = self._get_full_url("get_jwt_token")
        scopes = SCOPES_LIST_PARTNER if self.is_partner else SCOPES_LIST_COMPANY
        payload = {"key": self.api_token, "scopes": scopes}
        response = self.session.post(request_url, json=payload)
        validate_response(response)
        return response.json().get("jwt")

    def test_connectivity(self):
        """
        Test connectivity to the IronScales.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url(
            "test_connectivity", company_id=self.company_id
        )
        response = self.session.get(request_url)
        validate_response(response, "Unable to connect to IronScales.")

    def get_incident_details(self, incident_id):
        """
        Get incident details
        :param incident_id: {str} Id of the incident
        :return: {Incident}
        """
        request_url = self._get_full_url(
            "get_incident_details", company_id=self.company_id, incident_id=incident_id
        )
        response = self.session.get(request_url)
        validate_response(response, "Unable to get incident details")
        return self.parser.build_incident_object(response.json())

    def classify_incident(
        self, incident_id, new_classification, old_classification, user_email
    ):
        """
        Change incident classification
        :param incident_id: {str} Id of the incident
        :param new_classification: {str} New classification to apply to the incident
        :param old_classification: {str} Previous classification of the incident
        :param user_email: {str} User's email, who's performing the change
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url(
            "classify_incident", company_id=self.company_id, incident_id=incident_id
        )
        payload = {
            "classification": new_classification,
            "prev_classification": old_classification,
            "classifying_user_email": user_email,
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to change incident classification")

    def get_mitigation_impersonation_details(self, time_period):
        """
        Get mitigation impersonation details
        :param time_period: {int} Time period for which to get details
        :return: {list} List of Impersonation objects
        """
        request_url = self._get_full_url(
            "get_impersonation_details", company_id=self.company_id
        )
        params = {"period": time_period}
        response = self.session.get(request_url, params=params)
        validate_response(response, "Unable to get mitigation impersonation details")
        return self.parser.build_impersonations(raw_data=response.json())

    def get_incident_mitigation_details(self, time_period):
        """
        Get mitigation impersonation details
        :param time_period: {int} Time period for which to get details
        :return: {list} List of Mitigation objects
        """
        request_url = self._get_full_url(
            "get_mitigation_details", company_id=self.company_id
        )
        params = {"period": time_period}
        response = self.session.get(request_url, params=params)
        validate_response(response, "Unable to get incident mitigation details")
        return self.parser.build_impersonations(raw_data=response.json())

    def get_mitigations_per_mailbox(self, incident_ids, time_period, max_pages):
        """
        Get details of mitigations per mailbox
        :param incident_ids: {list} List of incident ids
        :param time_period: {int} Time period for which to get details
        :param max_pages: {int} Max number of pages to fetch
        :return: {list} List of Mitigation objects
        """
        request_url = self._get_full_url(
            "get_mitigations_per_mailbox", company_id=self.company_id
        )
        payload = {"incidents": incident_ids, "period": time_period}
        return [
            self.parser.build_mitigation_object(mitigation_json)
            for mitigation_json in self._paginate_results(
                method="POST", url=request_url, max_pages=max_pages, body=payload
            )
        ]

    def _paginate_results(
        self,
        method,
        url,
        result_key="mitigations",
        max_pages=DEFAULT_PAGE_QTY,
        params=None,
        body=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param result_key: {str} The key to extract data
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        body["page"] = 1
        response = self.session.request(method, url, params=params, json=body)
        validate_response(response, err_msg)
        results = response.json().get(result_key, [])

        while body["page"] < response.json().get("total_pages", 0):
            if response.json().get("page", 0) >= max_pages:
                break
            body["page"] = body["page"] + 1
            response = self.session.request(method, url, params=params, json=body)
            validate_response(response, err_msg)
            results.extend(response.json().get(result_key, []))

        return results
