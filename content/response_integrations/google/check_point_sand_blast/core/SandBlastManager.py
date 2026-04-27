# ============================================================================#
# title           :SandBlastManager.py
# description     :This Module contain all SabdBlast operations functionality
# author          :avital@siemplify.co
# date            :23-09-2020
# python_version  :3.7
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests
from typing import List, Optional
import json

from .SandBlastParser import SandBlastParser
from . import datamodels
from . import exceptions


class SandBlastManager:
    """
    SandBlast Manager
    """

    def __init__(self, api_root, api_key, verify_ssl=False):
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.session = requests.Session()
        self.session.headers = {"Authorization": api_key, "te_cookie": "remember"}
        self.session.verify = verify_ssl
        self.parser = SandBlastParser()

    def test_connectivity(self):
        """
        Test connectivity to Check Point SandBlast server
        :return: {bool} True if successfully connected, exception otherwise
        """
        self.query("8dfa1440953c3d93daafeae4a5daa326", ["te"])

    def upload_file(
        self, file_path: str, file_name: str, features: List[str]
    ) -> datamodels.QueryResponse:
        """
        Upload a file for analysis
        :param file_path: {str} The path to the file
        :param file_name: {str} The display name of the uploaded file
        :param features: {list}
        :return: {datamodels.QueryResponse} The query response matching the uploaded file
        """
        payload = {
            "request": {
                "file_name": file_name,
                "features": features,
                "te": {"reports": ["pdf", "xml"]},
            }
        }

        response = self.session.post(
            url=f"{self.api_root}/upload",
            files={"file": open(file_path, "rb"), "request": json.dumps(payload)},
        )

        self.validate_response(response, "Unable to upload file")

        # Update cookie to make sure all query requests go to the same server
        self.session.headers.update(
            {"te_cookie": response.cookies.get("te_cookie", "remember")}
        )

        return self.parser.build_siemplify_query_response_obj(
            response.json().get("response", {})
        )

    def query(
        self,
        file_hash: str,
        features: List[str],
        file_name: Optional[str] = "untitled.doc",
    ) -> datamodels.QueryResponse:
        """
        Upload a file for analysis
        :param file_path: {str} The path to the file
        :param file_name: {str} The display name of the uploaded file
        :param features: {list}
        :return: {datamodels.QueryResponse} The query response matching the uploaded file
        """
        hash_type = self.get_hash_type(file_hash)

        payload = {
            "request": [
                {
                    "file_name": file_name,
                    "features": features,
                    "te": {"reports": ["summary", "xml"]},
                    hash_type: file_hash,
                }
            ]
        }

        response = self.session.post(url=f"{self.api_root}/query", json=payload)

        self.validate_response(response, f"Unable to query {file_hash}")

        # Update cookie to make sure all query requests go to the same server
        self.session.headers.update(
            {"te_cookie": response.cookies.get("te_cookie", "remember")}
        )

        if not response.json().get("response"):
            raise exceptions.SandBlastManagerError(
                f"Query results were not found for {file_hash}"
            )

        return self.parser.build_siemplify_query_response_obj(
            response.json()["response"][0]
        )

    @staticmethod
    def is_successful_upload(query_response: datamodels.QueryResponse) -> bool:
        """
        Determine if an upload is successful
        :param query_response: {datamodels.QueryResponse} The upload query result object
        :return: {bool} True if upload is considered as successful, False otherwise.
        """
        return query_response.status.code in [
            datamodels.StatusCodes.FOUND,
            datamodels.StatusCodes.UPLOAD_SUCCESS,
            datamodels.StatusCodes.PENDING,
            datamodels.StatusCodes.PARTIALLY_FOUND,
        ]

    @staticmethod
    def is_failed_upload(query_response):
        return query_response.status.code in [
            datamodels.StatusCodes.FILE_TYPE_NOT_SUPPORTED,
            datamodels.StatusCodes.NOT_FOUND,
            datamodels.StatusCodes.NO_QUOTA,
            datamodels.StatusCodes.BAD_REQUEST,
            datamodels.StatusCodes.INTERNAL_ERROR,
            datamodels.StatusCodes.FORBIDDEN,
            datamodels.StatusCodes.NOT_ENOUGH_RESOURCES,
        ]

    @staticmethod
    def is_scan_running(query_response: datamodels.QueryResponse) -> bool:
        """
        Determine if a scan is still running
        :param query_response: {datamodels.QueryResponse} The query result object
        :return: {bool} True if scan is still runninf, False otherwise.
        """
        return query_response.status.code in [
            datamodels.StatusCodes.UPLOAD_SUCCESS,
            datamodels.StatusCodes.PENDING,
        ]

    @staticmethod
    def is_scan_completed(query_response: datamodels.QueryResponse) -> bool:
        """
        Determine if a scan has completed
        :param query_response: {datamodels.QueryResponse} The query result object
        :return: {bool} True if scan is considered as completed, False otherwise.
        """
        return query_response.status.code in [
            datamodels.StatusCodes.FOUND,
            datamodels.StatusCodes.PARTIALLY_FOUND,
        ]

    @staticmethod
    def is_scan_failed(query_response: datamodels.QueryResponse) -> bool:
        """
        Determine if a scan has failed
        :param query_response: {datamodels.QueryResponse} The query result object
        :return: {bool} True if scan is considered as failed, False otherwise.
        """
        return query_response.status.code in [
            datamodels.StatusCodes.NO_QUOTA,
            datamodels.StatusCodes.NOT_FOUND,
            datamodels.StatusCodes.BAD_REQUEST,
            datamodels.StatusCodes.INTERNAL_ERROR,
            datamodels.StatusCodes.FORBIDDEN,
            datamodels.StatusCodes.NOT_ENOUGH_RESOURCES,
            datamodels.StatusCodes.FILE_TYPE_NOT_SUPPORTED,
        ]

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate a response
        :param response: {requests.Response} The response
        :param error_msg: {unicode} The error message to display on failure
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise exceptions.SandBlastManagerError(
                f"{error_msg}: {error} {response.text}"
            )

    @staticmethod
    def get_hash_type(file_hash: str) -> str:
        """
        Get the type of a hash by its length
        :param file_hash: {str} The hash
        :return: {str} The type of the hash
        """
        # The three hash types supported by checkpoint as of 3/30/20
        if len(file_hash) == 32:
            return datamodels.HashTypes.MD5
        elif len(file_hash) == 64:
            return datamodels.HashTypes.SHA256
        elif len(file_hash) == 40:
            return datamodels.HashTypes.SHA1

        raise exceptions.SandBlastValidationError(
            "Invalid hash type. Supported types: MD5, SHA1, SHA256."
        )
