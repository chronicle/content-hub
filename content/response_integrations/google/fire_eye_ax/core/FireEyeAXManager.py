from __future__ import annotations
from urllib.parse import urljoin
import requests
import json

from .FireEyeAXParser import FireEyeAXParser
from .UtilsManager import validate_response
from .constants import ENDPOINTS, HEADERS


class FireEyeAXManager:

    def __init__(
        self, api_root, username, password, verify_ssl=False, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the FireEye AX instance.
        :param username: Username of FireEye AX account.
        :param password: Password of FireEye AX account.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the FireEye AX server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.username = username
        self.password = password
        self.siemplify_logger = siemplify_logger
        self.parser = FireEyeAXParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.auth = (self.username, self.password)
        self.api_token = self.obtain_token()
        self.session.headers.update({"X-FeApi-Token": self.api_token})
        self.session.auth = None

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def obtain_token(self):
        """
        Obtain FireEye AX authentication security token.
        :return: {str} token
        """
        request_url = self._get_full_url("authorize")
        response = self.session.post(request_url)
        validate_response(response)
        return response.headers.get("X-FeApi-Token")

    def test_connectivity(self):
        """
        Test connectivity to the FireEye AX.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("ping")
        response = self.session.get(request_url)
        validate_response(response, "Unable to connect to FireEye AX.")

    def get_appliance_details(self):
        """
        Get appliance details
        :return: {dict} Appliance details
        """
        request_url = self._get_full_url("get_appliance_details")
        response = self.session.get(request_url)
        validate_response(response)

        return response.json()

    def get_data(
        self, priority, profile, application, force_rescan, analysis_type, url
    ):
        """
        Get entity data
        :param priority: {int} Priority for submission
        :param profile: {str} VM profile to use
        :param application: {str} ID of application to use
        :param force_rescan: {bool} If True, will force to rescan the submitted file
        :param analysis_type: {int} Type of analysis to do
        :param url: {str} File url to analyze
        :return: {Submission} Submission object
        """
        request_url = self._get_full_url("get_data")
        payload = {
            "timeout": 200,
            "priority": priority,
            "profiles": [profile],
            "application": application if application else 0,
            "force": force_rescan,
            "analysistype": analysis_type,
            "prefetch": 1,
            "urls": [url],
        }

        response = self.session.post(request_url, json=payload)
        validate_response(response)

        return self.parser.build_submission_object(response.json())

    def get_submission_status(self, submission_id):
        """
        Get the status of submission
        :param submission_id: {str} ID of submission
        :return: {Submission} Submission object
        """
        request_url = self._get_full_url(
            "get_submission_status", submission_id=submission_id
        )
        response = self.session.get(request_url)
        validate_response(response)

        return self.parser.build_submission_object(response.json())

    def get_submission_details(self, result_id):
        """
        Get the details of submission
        :param result_id: {str} ID of submission
        :return: {SubmissionResult} SubmissionResult object
        """
        request_url = self._get_full_url("get_submission_details", result_id=result_id)
        response = self.session.get(request_url)
        validate_response(response)

        return self.parser.build_submission_result_object(response.json())

    def submit_file(
        self, file_path, priority, profile, application, force_rescan, analysis_type
    ):
        """
        Submit file for analysis
        :param file_path: {str} Path of file to submit
        :param priority: {int} Priority for submission
        :param profile: {str} VM profile to use
        :param application: {str} ID of application to use
        :param force_rescan: {bool} If True, will force to rescan the submitted file
        :param analysis_type: {int} Type of analysis to do
        :return: {Submission} Submission object
        """
        request_url = self._get_full_url("submit_file")
        options = {
            "timeout": 500,
            "priority": priority,
            "profiles": [profile],
            "application": application if application else 0,
            "force": force_rescan,
            "analysistype": analysis_type,
            "prefetch": 0,
        }
        payload = {"options": json.dumps(options)}

        try:
            with open(file_path, "rb") as file_to_upload:
                files = [("filename", file_to_upload)]
                self.session.headers.pop("Content-Type", None)
                response = self.session.post(request_url, data=payload, files=files)
                validate_response(response)

                return self.parser.build_file_submission_object(response.json())
        except IOError:
            raise IOError(
                f"the following file was not found or action doesn't have enough permissions to access "
                f"it: {file_path}"
            )
