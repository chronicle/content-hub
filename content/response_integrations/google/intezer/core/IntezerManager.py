from __future__ import annotations

from io import BytesIO
from typing import Optional
import hashlib
import json
import os
import time

from urllib.parse import urljoin
import requests
import requests.adapters
from intezer.core import constants
from intezer.core.datamodels import (
    Detonate,
    SubmitAlert,
    Alert,
    URLReport,
    IndexFile,
    SubmitEmail,
    FileAnalysis,
    FileAnalysisResult,
    SubAnalysis,
    Ioc,
    Ttps,
    SubAnalysisMetaData,
    SubAnalysisCodeReuse,
    Id,
)
from intezer.core.exceptions import IntezerUserInputError, IntezerManagerError
from intezer.core import IntezerParser as parser
from intezer.core import UtilsManager

MALICIOUS_VERDICTS = ["malicious", "suspicious"]


class IntezerManager:
    """Intezer Manager Class"""

    def __init__(
        self, api_root: str, api_key: str, verify_ssl: bool, siemplify_logger=None
    ):
        """The method is used to initialize an object of Manager class

        Args:
            api_root: API root for Intezer API
            api_key: API Key for Intezer account
            verify_ssl: Specifies if certificate that is configured on the api
                root should be validated
            siemplify_logger: Siemplify logger
        """
        self.api_root = api_root
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.session = requests.session()
        self.session.verify = verify_ssl
        access_token = self.obtain_access_token(self.api_key)
        self.session.headers["Authorization"] = f"Bearer {access_token}"

    def obtain_access_token(self, api_key: str) -> str:
        """Perform login and obtain access token.

        Args:
            api_key: The id of url
        Returns:
            The access token
        """
        url = self._get_full_url(constants.GET_ACCESS_TOKEN)
        response = self.session.post(url, json={"api_key": api_key})
        UtilsManager.validate_response(
            response=response, error_msg="Unable to obtain token"
        )
        return response.json().get("result")

    def _get_full_url(self, url_id: str, **kwargs: Optional[dict, str]) -> str:
        """Get full url from url identifier.

        Args:
            url_id: The id of url
            kwargs: Variables passed for string formatting
        Returns:
            The full url for the API request
        """
        return urljoin(self.api_root, constants.ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self) -> None:
        """Test connectivity"""
        url = self._get_full_url(constants.TEST_CONNECTIVITY)
        response = self.session.get(url)
        UtilsManager.validate_response(response=response)

    def get_detonate_url(self, detonate_url: str) -> Detonate:
        """Analyze a url.

        Args:
            detonate_url: The url to analyze.
        Returns:
            A Detonate object
        """
        url = self._get_full_url(constants.DETONATE_URL)
        response = self.session.post(
            url, json={"url": detonate_url, "requester": constants.REQUESTER}
        )
        UtilsManager.validate_response(response=response)
        return parser.build_detonate_object(
            raw_data=response.json(),
            analysis_id=UtilsManager.get_id_from_response(response=response),
            analysis_status=constants.CREATED_STATUS,
            analysis_type="url",
            identifier=detonate_url,
        )

    def get_detonate_hash(self, detonate_hash: str) -> Detonate:
        """Analyze the url.

        Args:
            detonate_hash: The url to analyze.
        Returns:
            A Detonate object
        """
        url = self._get_full_url(constants.DETONATE_HASH)
        response = self.session.post(
            url, json={"hash": detonate_hash, "requester": constants.REQUESTER}
        )
        UtilsManager.validate_response(response=response)
        return parser.build_detonate_object(
            raw_data=response.json(),
            analysis_id=UtilsManager.get_id_from_response(response=response),
            analysis_status=constants.CREATED_STATUS,
            analysis_type="file",
            identifier=detonate_hash,
        )

    def get_detonate_file(self, file_path: str, related_alert_ids: str) -> Detonate:
        """Analyze a File.

        Args:
            file_path: The file path to analyze.
            related_alert_ids: related alert ids
        Returns:
            A Detonate object
        """
        UtilsManager.is_valid_file_path(file_path=file_path)
        with open(file_path, "rb") as file_to_upload:
            url = self._get_full_url(constants.DETONATE_FILE)
            files = {"file": ("file_name", file_to_upload)}
            params = {"requester": constants.REQUESTER}
            if related_alert_ids:
                params["related_alert_ids"] = [related_alert_ids]
            response = self.session.post(url, files=files, json=params)
            UtilsManager.validate_response(
                response=response, error_msg=f"Unable to submit file {file_path}"
            )
            return parser.build_detonate_object(
                raw_data=response.json(),
                analysis_id=UtilsManager.get_id_from_response(response=response),
                analysis_status=constants.CREATED_STATUS,
                analysis_type="file",
                identifier=file_path,
            )

    def index_file_hash_by_id(self, index_id: str) -> IndexFile:
        """Get the result URL from an index hash.

        Args:
            index_id (str): The index id of the file hash to index.
        Returns:
            An IndexFile object
        """
        url = self._get_full_url(constants.INDEX_FILE_BY_ID, index_id=index_id)

        response = self.session.get(url)
        UtilsManager.validate_response(response=response)
        return parser.build_index_file_object(raw_data=response.json())

    def get_index_id_from_file_hash(
        self, index_as: constants.IndexType, sha256: str = None, family_name: str = None
    ) -> Optional[Id, None]:
        """Get Index Id from file hash.

        Args:
            index_as: The type of classification of this file.
            sha256: The sha256 of the file to index.
            family_name: The family name to index as
        Returns:
            An Index Id object
        """
        url = self._get_full_url(constants.INDEX_FILE_BY_HASH, sha256=sha256)
        data = {"index_as": index_as.value}

        if family_name:
            data["family_name"] = family_name

        response = self.session.post(url, json=data)
        try:
            UtilsManager.validate_response(response=response)
        except IntezerManagerError:
            return None
        return parser.build_id_object(raw_data=response.json())

    def details_index_file(self, sha256: str) -> IndexFile:
        """Index a file.

        Args:
            sha256: The SHA256
        Returns:
            An IndexFile object
        """
        url = self._get_full_url(constants.INDEX_FILE_BY_HASH, sha256=sha256)
        response = self.session.get(url)
        UtilsManager.validate_response(response=response)
        return parser.build_index_unset_file_object(
            raw_data=response.json(), status=response.status_code
        )

    def unset_index_file(self, sha256: str) -> IndexFile:
        """Unset the Index file.

        Args:
            sha256: The SHA256
        Returns:
            An IndexFile object
        """
        url = self._get_full_url(constants.UNSET_INDEX_FILE_BY_HASH, sha256=sha256)
        response = self.session.delete(url)
        UtilsManager.validate_response(response=response)
        return parser.build_index_unset_file_object(
            raw_data=response.json(), status=response.status_code
        )

    def get_alert(self, alert_id: str) -> Alert:
        """Get alert.

        Args:
            alert_id: alert id to search for.
        Returns:
            An alert object
        """
        url = self._get_full_url(constants.GET_ALERT)
        data = {"alert_id": alert_id}
        response = self.session.post(url, json=data)
        UtilsManager.validate_response(response=response)
        return parser.build_get_alert_object(raw_data=response.json())

    def submit_alert(
        self, alert_source: str, alert_json: dict, alert_mapping: dict
    ) -> SubmitAlert:
        """Get alert.

        Args:
            alert_source: The source of the alert
            alert_json: The raw alert JSON object
            alert_mapping: The definition mapping for the alert
        Returns:
            An alert Object
        """
        url = self._get_full_url(constants.SUBMIT_ALERT)
        data = {
            "alert": alert_json,
            "definition_mapping": alert_mapping,
            "alert_source": alert_source,
        }
        response = self.session.post(url, json=data)
        UtilsManager.validate_response(response=response)
        return parser.build_submit_alert_object(raw_data=response.json())

    def get_url_report(self, analysis_id: str) -> URLReport:
        """Get URL Report.

        Args:
            analysis_id: The analysis id of an url
        Returns:
            An URLReport Object
        """
        url = self._get_full_url(constants.GET_URL_REPORT, analysis_id=analysis_id)
        response = self.session.get(url)
        UtilsManager.validate_response(response=response)
        return parser.build_get_url_report_object(raw_data=response.json())

    def submit_suspicious_email(self, raw_email: str) -> SubmitEmail:
        """Submit suspicious email

        Args:
            raw_email: The path to the email file

        Returns:
            A SubmitEmail object
        """
        additional_info: Optional[dict] = None
        with open(raw_email, "rb") as email_file:
            file_stream = BytesIO(email_file.read())
        file = UtilsManager.parse_file_from_file_stream(file_stream)
        alert = file_stream

        send_alert_params = {
            "alert_source": "phishing_emails",
            "environment": None,
            "display_fields": ",".join(
                ["reported_by", "sender", "received", "subject", "message_id", "to"]
            ),
            "default_verdict": None,
            "alert_sender": None,
            "additional_info": (
                json.dumps(additional_info) if additional_info else None,
            ),
        }
        send_alert_params = {
            key: value for key, value in send_alert_params.items() if value is not None
        }

        url = self._get_full_url(constants.SUBMIT_EMAIL)
        file = {"file": (file, alert)}
        response = self.session.post(url, data=send_alert_params, files=file)
        UtilsManager.validate_response(response=response)
        return parser.build_submit_email_object(raw_data=response.json())

    def get_file_analysis_result(
        self, analysis_id: str = None, file_hash: str = None, private_only: bool = False
    ) -> FileAnalysisResult:
        """Get Analysis of the file.

        Args:
            analysis_id: The analysis ID of the file to retrieve analysis for.
            file_hash: The hash of the file to retrieve analysis for.
            private_only: A flag to filter results by private analyses only.
        Returns:
            FileAnalysis Result object containing the analysis
        """

        body = {}
        url = None
        if analysis_id:
            url = self._get_full_url(
                constants.GET_FILE_REPORT_BY_ANALYSIS_ID, analysis_id=analysis_id
            )

        elif file_hash:
            url = self._get_full_url(
                constants.GET_FILE_REPORT_BY_FILE_HASH, hash_value=file_hash
            )
            body["should_get_only_private_analysis"] = private_only

        response = self.session.get(url, json=body)
        UtilsManager.validate_response(response=response)
        return parser.build_file_analysis_result_object(raw_data=response.json())

    def get_iocs(self, analysis_id: str) -> Optional[Ioc]:
        """Get Ioc data for a given analysis.

        Args:
            analysis_id: The analysis ID of the file to retrieve analysis for.
        Returns:
            Ioc object for an analysis id
        """
        url = self._get_full_url(constants.GET_IOCS, analysis_id=analysis_id)
        response = self.session.get(url)
        try:
            UtilsManager.validate_response(response=response)
        except IntezerUserInputError:
            return None
        return parser.build_iocs_object(raw_data=response.json())

    def get_dynamic_ttps(self, analysis_id: str) -> Optional[Ttps]:
        """Get Ioc data for a given analysis.

        Args:
            analysis_id: The analysis ID of the file to retrieve analysis for.
        Returns:
            Ttps object for an analysis id
        """
        url = self._get_full_url(constants.GET_DYNAMIC_TTPS, analysis_id=analysis_id)
        response = self.session.get(url)
        try:
            UtilsManager.validate_response(response=response)
        except IntezerUserInputError:
            return None
        return parser.build_ttps_object(raw_data=response.json())

    def get_sub_analyses_by_id(self, analysis_id: str) -> Optional[SubAnalysis]:
        """Get Ioc data for a given analysis.

        Args:
            analysis_id: The analysis ID of the file to retrieve analysis for.
        Returns:
            SubAnalysis object for an analysis id
        """
        url = self._get_full_url(
            constants.GET_SUB_ANALYSES_IDS, analysis_id=analysis_id
        )
        response = self.session.get(url)
        try:
            UtilsManager.validate_response(response=response)
        except IntezerUserInputError:
            return None
        return parser.build_sub_analyses_object(raw_data=response.json())

    def get_sub_analysis_metadata_by_id(
        self, analysis_id: str, sub_analysis_id: str
    ) -> Optional[SubAnalysisMetaData]:
        """Get Ioc data for a given analysis.

        Args:
            analysis_id: The analysis ID of the file to retrieve analysis for.
            sub_analysis_id: The sub analysis ID of the file to retrieve
        Returns:
            SubAnalysis object for an analysis id
        """
        url = self._get_full_url(
            constants.GET_FILE_METADATA,
            analysis_id=analysis_id,
            sub_analysis_id=sub_analysis_id,
        )
        response = self.session.get(url)
        try:
            UtilsManager.validate_response(response=response)
        except IntezerUserInputError:
            return None
        return parser.build_sub_analysis_metadata_object(raw_data=response.json())

    def get_sub_analysis_code_reuse_by_id(
        self, analysis_id: str, sub_analysis_id: str
    ) -> Optional[SubAnalysisCodeReuse]:
        """Get Ioc data for a given analysis.

        Args:
            analysis_id: The analysis ID of the file to retrieve analysis for.
            sub_analysis_id: The sub analysis ID of the file to retrieve
        Returns:
            SubAnalysisCodeReuse object for an analysis id
        """
        url = self._get_full_url(
            constants.GET_CODE_REUSE,
            analysis_id=analysis_id,
            sub_analysis_id=sub_analysis_id,
        )
        response = self.session.get(url)
        try:
            UtilsManager.validate_response(response=response)
        except IntezerUserInputError:
            return None
        return parser.build_sub_analysis_code_reuse_object(raw_data=response.json())

    def get_file_report(
        self, analysis_id: str = None, file_hash: str = None, private_only: bool = False
    ) -> Optional[FileAnalysis]:
        """Get File Analysis for a given analysis.

        Args:
            analysis_id: The analysis ID of the file to retrieve analysis for.
            file_hash: The hash of the file to retrieve analysis for.
            private_only: A flag to filter results by private analyses only.
        Returns:
            FileAnalysis object containing the complete analysis
        """
        file_analysis_result = self.get_file_analysis_result(
            analysis_id, file_hash, private_only
        )
        if file_analysis_result:
            metadata = code_reuse = None
            iocs = self.get_iocs(file_analysis_result.analysis_id)
            dynamic_ttps = self.get_dynamic_ttps(file_analysis_result.analysis_id)
            sub_analysis = self.get_sub_analyses_by_id(file_analysis_result.analysis_id)
            if sub_analysis:
                metadata = self.get_sub_analysis_metadata_by_id(
                    file_analysis_result.analysis_id, sub_analysis.sub_analysis_id
                )
                code_reuse = self.get_sub_analysis_code_reuse_by_id(
                    file_analysis_result.analysis_id, sub_analysis.sub_analysis_id
                )

            analysis = {
                "analysis": file_analysis_result.to_json(),
                "iocs": iocs.to_json() if iocs else None,
                "ttps": dynamic_ttps.to_json() if dynamic_ttps else None,
                "metadata": metadata.to_json() if metadata else None,
                "root-code-reuse": code_reuse.to_json() if code_reuse else None,
            }
            return parser.build_file_analysis_object(
                status=file_analysis_result.status, analysis=analysis
            )
        return None

    def get_existing_analysis(self, file_hash: str) -> Optional[dict, None]:
        """Get existing analysis report of a hash if it exists

        Args:
            file_hash: The hash
        Returns:
            Analysis report if exists, None otherwise.
        """
        response = self.session.get(f"{constants.API_URL}/files/{file_hash}")

        if response.status_code == 404:
            # Hash analysis doesn't exist -return None
            return None

        UtilsManager.validate_response(
            response, f"Unable to get existing analysis of {file_hash}"
        )
        return response.json().get("result")

    def submit_file(self, file_path: str) -> str:
        """Submit a file for analysis

        Args:
            file_path: The path of the file
        Returns:
            The url to query the result for
        """
        if not os.path.exists(file_path):
            raise IntezerManagerError(f"File {file_path} doesn't exist.")

        with open(file_path, "rb") as file_to_upload:
            files = {"file": ("file_name", file_to_upload)}

            response = self.session.post(f"{constants.API_URL}/analyze", files=files)
            UtilsManager.validate_response(
                response, f"Unable to submit file {file_path}"
            )

            return response.json()["result_url"]

    def submit_hash(self, file_hash: str) -> str:
        """Submit a hash for analysis

        Args:
            file_hash: The has of the file
        Returns:
            The url to query the result for
        """
        response = self.session.post(
            f"{constants.API_URL}/analyze-by-hash", json={"hash": file_hash}
        )
        if response.status_code == 404:
            raise IntezerManagerError(
                f"Hash {file_hash} is not available in Intezer Analyze"
            )
        UtilsManager.validate_response(response, f"Unable to submit hash {file_hash}")

        return response.json()["result_url"]

    def get_results(self, results_url: str) -> dict:
        """Get analysis results

        Args:
            results_url: The url to query results for
        Returns:
            The analysis results (report)
        """
        while not self.is_analysis_completed(results_url):
            time.sleep(1)

        if self.is_analysis_failed(results_url):
            response = self.session.get(f"{constants.API_URL}{results_url}")
            raise IntezerManagerError(
                f"Analysis failed. Error: {response.json().get('error')}"
            )

        response = self.session.get(f"{constants.API_URL}{results_url}")
        return response.json().get("result")

    def is_analysis_completed(self, results_url: str) -> bool:
        """Check whether an analysis has completed or not

        Args:
            results_url: The url to query results for
        Returns:
            True if completed, otherwise False.
        """
        response = self.session.get(f"{constants.API_URL}{results_url}")
        UtilsManager.validate_response(
            response, f"Unable to get results for {results_url}"
        )
        return response.json().get("status") in [
            constants.SUCCESS_STATUS,
            constants.FAILED_STATUS,
        ]

    def is_analysis_failed(self, results_url: str) -> bool:
        """Check whether an analysis has failed or not

        Args:
            results_url: The url to query results for
        Results:
            True if failed, otherwise False.
        """
        response = self.session.get(f"{constants.API_URL}{results_url}")
        UtilsManager.validate_response(
            response, f"Unable to get results for {results_url}"
        )
        return response.json().get("status") == constants.FAILED_STATUS

    def is_analysis_succeeded(self, results_url: str) -> bool:
        """Check whether an analysis has succeeded or not

        Args:
            results_url: {str} The url to query results for
        Returns:
            True if succeeded, otherwise False.
        """
        response = self.session.get(f"{constants.API_URL}{results_url}")
        UtilsManager.validate_response(
            response, f"Unable to get results for {results_url}"
        )
        return response.json().get("status") == constants.SUCCESS_STATUS

    @staticmethod
    def md5(file_path: str) -> str:
        """Generate a md5 hash of a file

        Args:
            file_path: The path of the file
        Returns:
            The md5 of the file
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def sha256(file_path: str) -> str:
        """Generate a sha256 hash of a file

        Args:
            file_path: The path of the file
        Returns:
            The sha256 of the file
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
