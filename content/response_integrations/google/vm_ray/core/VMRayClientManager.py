from __future__ import annotations

import copy
import requests
from .VMRayParser import VMRayParser
from .VMRayExceptions import VMRayApiException
from .constants import (
    API_ENDPOINTS,
    ALREADY_EXIST_URL_ERROR,
    DEFAULT_SCORE,
    MD5,
    SHA1,
    SHA256,
    IOC_TYPE_MAPPING,
    IOC_VERDICT_MAPPING,
)
from .datamodels import SampleThreatIndicator
from .UtilsManager import get_type_of_hash, validate_response


class VMRayClient:
    """
    VMRay api client
    """

    def __init__(
        self,
        host,
        api_key,
        verify_ssl=False,
        siemplify_logger=None,
        platform_version="",
        integration_version="",
    ):
        """
        The method is used to init an object of Manager class
        :param host: {str} API host
        :param api_key: {str} API Key of the SumoLogicCloudSIEM instance
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        :param platform_version: {str} siemplify platform version
        :param integration_version: {int} integration version
        """
        self.host = host
        self.logger = siemplify_logger
        self.session = requests.session()
        self.session.headers = {
            "Authorization": "api_key " + api_key,
            "User-Agent": f"Platform: Siemplify {platform_version}. Integration version: {integration_version}",
        }
        self.session.verify = verify_ssl
        self.parser = VMRayParser()

    def test_connectivity(self):
        """
        Simple get request to see if connected
        :return: {void}
        """
        response = self.session.get(API_ENDPOINTS["analysis_limit"].format(self.host))
        validate_response(response)

    def get_by_value(self, query, value):
        """
        Get by value
        :param query: {str} query format
        :param value: {str/int} search filter (hash_value OR sample_id)
        :return: {dict} sample details
        """
        response = self.session.get(f"{self.host}{query}{value}")
        validate_response(response)
        data_json = response.json()
        return data_json.get("data")

    def get_sample_by_id(self, sample_id):
        """
        Get sample by ID
        :param sample_id: {str/int}
        :return {dict}: sample details
        """
        if not sample_id:
            raise VMRayApiException("Sample id is None")

        res_json = self.get_by_value(API_ENDPOINTS["sample"], sample_id)

        if res_json:
            return self.parser.build_sample_analyses_object(res_json)

        return None

    def is_submission_finished(self, submission_id):
        """
        Determine whether submission is done
        :param submission_id: {str}
        :return: {bool}
        """
        if not submission_id:
            raise VMRayApiException("SubmissionID is None")

        res = self.get_by_value(API_ENDPOINTS["submission"], submission_id)
        return res.get("submission_finished")

    def get_sample_by_hash(self, hash_value):
        """
        Get all samples created on specified hash
        :param hash_value: {str} fash value
        :return: SampleAnalyses: Sample analyses object or None
        """
        hash_type = get_type_of_hash(hash_value)
        hashes = None

        if hash_type == MD5:
            hashes = self.get_by_value(API_ENDPOINTS["sample_md5"], hash_value)
        elif hash_type == SHA1:
            hashes = self.get_by_value(API_ENDPOINTS["sample_sha1"], hash_value)
        elif hash_type == SHA256:
            hashes = self.get_by_value(API_ENDPOINTS["sample_sha256"], hash_value)
        if hashes:
            return self.parser.build_sample_analyses_object(hashes[0])
        else:
            return None

    def submit_sample_file(self, sample_file, tags=None, comment=None):
        """
        :param sample_file: {str} file path
        :param tags: {str} Comma separated tags to add
        :param comment: {str} Comment to add
        :return: {dict} sample details
        """
        query = API_ENDPOINTS["sample_submit"]
        url = f"{self.host}{query}"
        params = {}

        if tags:
            params["tags"] = tags
        if comment:
            params["comment"] = comment

        response = self.session.post(
            url, params=params, files={"sample_file": open(sample_file, "rb")}
        )
        validate_response(response)
        data_json = response.json()

        # Check if upload succeed
        if data_json.get("data", {}).get("errors", []):
            # Check if URL Already submitted
            if ALREADY_EXIST_URL_ERROR in data_json.get("data", {}).get("errors", [])[
                0
            ].get("error_msg", ""):
                # Fetch the existing URL report
                sample_id = data_json["data"]["samples"][0]["sample_id"]
                return self.get_sample_by_id(sample_id)
            else:
                raise VMRayApiException(
                    f"Failed to submit {sample_file}. Error: {data_json['data']['errors'][0]['error_msg']}"
                )

        data = data_json.get("data", {})
        return self.parser.build_sample_res_object(data) if data else None

    def submit_url_for_browser_analysis(self, sample_url, tags=None, comment=None):
        """
        Submit a url for analysis
        :param sample_url: {str} The url to analyze
        :param tags: {str} Comma separated tags to add
        :param comment: {str} Comment to add
        :return: {dict} sample details
        """
        query = API_ENDPOINTS["sample_submit"]
        url = f"{self.host}{query}"

        params = {"sample_url": sample_url}

        if tags:
            params["tags"] = tags
        if comment:
            params["comment"] = comment

        response = self.session.post(url, params=params)
        validate_response(response)
        data_json = response.json()

        # Check if upload succeed
        if data_json.get("data", {}).get(
            "errors", []
        ) and ALREADY_EXIST_URL_ERROR not in data_json.get("data", {}).get("errors")[
            0
        ].get(
            "error_msg", ""
        ):
            raise VMRayApiException(
                f"Failed to submit {sample_url}. Error: {data_json.get('data', {}).get('errors')[0].get('error_msg')}"
            )

        return self.parser.build_sample_object(data_json)

    def get_sample_iocs(
        self, sample_id, ioc_type_filter=None, ioc_verdict_filter=None, limit=None
    ):
        """
        Get iocs of sample
        :param sample_id: {int} The sample id
        :param ioc_type_filter: {list} list of ioc types for filtering
        :param ioc_verdict_filter: {list} list of ioc verdicts for filtering
        :param limit: {int} limit for results per ioc type
        :return: {JSON} The iocs json (dict)
        """
        url = API_ENDPOINTS["sample_iocs"].format(self.host, sample_id)
        response = self.session.get(url)
        validate_response(response)
        filtered_iocs = self.filter_iocs(
            response.json().get("data", {}).get("iocs", {}),
            ioc_type_filter,
            ioc_verdict_filter,
            limit,
        )
        return self.parser.build_sample_iocs_object(filtered_iocs)

    @staticmethod
    def filter_iocs(iocs, ioc_type_filter, ioc_verdict_filter, limit):
        """
        Filter iocs
        :param iocs: {dict} dictionary of all iocs
        :param ioc_type_filter: {list} list of ioc types for filtering
        :param ioc_verdict_filter: {list} list of ioc verdicts for filtering
        :param limit: {int} limit for results per ioc type
        :return: {dict} filtered iocs
        """
        data = copy.deepcopy(iocs)

        for key, value in iocs.items():
            if ioc_type_filter and IOC_TYPE_MAPPING.get(key, "") not in ioc_type_filter:
                data.pop(key, None)
                continue

            if ioc_verdict_filter:
                data[key] = list(
                    filter(
                        lambda item: IOC_VERDICT_MAPPING.get(item.get("verdict", None))
                        in ioc_verdict_filter,
                        data.get(key, []),
                    )
                )

                data[key] = data[key][:limit] if limit else data[key]

        return data

    def get_sample_threat_indicators(
        self,
        sample_id: int,
        score: int = DEFAULT_SCORE,
        limit: int = None,
    ) -> list[SampleThreatIndicator]:
        """Get threat indicators of sample

        Args:
            sample_id (int): The sample id.
            score (int): Lowest score for filtering.
            limit (int): Limit for results.

        Returns:
            list[SampleThreatIndicator]: The threat indicators.
        """
        url = API_ENDPOINTS["sample_thread_indicators"].format(self.host, sample_id)
        response = self.session.get(url)
        validate_response(response)
        threat_indicators = response.json().get("data").get("threat_indicators", [])
        filtered_threat_indicators = self.filter_threat_indicators(
            threat_indicators, score, limit
        )
        return list(
            map(
                self.parser.build_sample_threat_indicator_object,
                filtered_threat_indicators,
            )
        )

    @staticmethod
    def filter_threat_indicators(threat_indicators, score, limit):
        """
        Filter threat indicators
        :param threat_indicators: {list} list of threat indicators
        :param score: {int} lowest score for filtering
        :param limit: {int} limit for results
        :return: {list} filtered threat indicators
        """
        data = [
            threat_indicator
            for threat_indicator in threat_indicators
            if threat_indicator.get("score") >= score
        ]
        data = sorted(
            data,
            key=lambda threat_indicator: threat_indicator.get("score"),
            reverse=True,
        )
        return data[:limit] if limit else data

    def get_json_analysis_archive(self, analysis_id):
        """
        Download JSON report of analysis
        :param analysis_id: {int} The analysis id
        :return: {str} The content of the JSON report
        """
        url = API_ENDPOINTS["analysis_archive_logs"].format(self.host, analysis_id)
        response = self.session.get(url)
        validate_response(response)
        return response.content

    def get_zip_analysis_archive(self, analysis_id):
        """
        Download zip report of analysis
        :param analysis_id: {int} The analysis id
        :return: {str} The content of the ZIP report
        """
        url = API_ENDPOINTS["analysis_archive"].format(self.host, analysis_id)
        response = self.session.get(url)
        validate_response(response)
        return response.content

    def get_last_analysis_id_by_sample(self, sample_id):
        """
        Get the id of last created analysis by sample id
        :param sample_id: {int} The sample id
        :return: {int} The id of the analysis
        """
        url = API_ENDPOINTS["analysis_sample"].format(self.host, sample_id)
        response = self.session.get(url)
        validate_response(response)

        # Get the ID of the last created analysis
        if response.json().get("data", {}):
            sorted_analysis = sorted(
                response.json().get("data", {}),
                key=lambda analysis: analysis.get("analysis_created"),
            )
            if sorted_analysis:
                return sorted_analysis[0].get("analysis_id", 0)

    def add_tag_to_submission(self, submission_id, tag_name):
        """
        Added tag to given submission
        :param submission_id: {int} The Submission ID
        :param tag_name: {str} The tag that need to be added
        :return: True if success
        """
        url = API_ENDPOINTS["submission_add_tag"].format(
            self.host, submission_id, tag_name
        )
        response = self.session.post(url)
        validate_response(response)
        return True

    def get_job_details(self, job_id):
        """
        Get job details
        :param job_id: {int} job id
        :return: {void}
        """
        url = API_ENDPOINTS["get_job"].format(self.host, job_id)
        response = self.session.get(url)
        validate_response(response)
