from __future__ import annotations

import json
from http import HTTPStatus
from shlex import quote

from google.auth.transport import Response, requests
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.rest.auth import build_credentials_from_sa

from ..core.config import Config
from ..core.utils import (
    build_base_url,
    build_sandbox_data_table_payload,
    build_sandbox_indicators_payload,
)


class DataTableManager:
    """Provides methods to manage IOCs and interact with DataTables"""

    def __init__(self, siemplify: SiemplifyAction) -> None:
        google_secops_project_id = quote(
            extract_configuration_param(
                siemplify, Config.INTEGRATION_NAME, param_name="Project ID", is_mandatory=True
            )
        )

        google_secops_project_location = quote(
            extract_configuration_param(
                siemplify, Config.INTEGRATION_NAME, param_name="Project location", is_mandatory=True
            )
        )

        google_secops_instance_id = quote(
            extract_configuration_param(
                siemplify, Config.INTEGRATION_NAME, param_name="Instance ID", is_mandatory=True
            )
        )

        google_secops_sevice_account_json = json.loads(
            quote(
                extract_configuration_param(
                    siemplify,
                    Config.INTEGRATION_NAME,
                    param_name="Google service account",
                    is_mandatory=True,
                )
            )
        )

        self._logger = siemplify.LOGGER
        self._http_session = requests.AuthorizedSession(
            build_credentials_from_sa(google_secops_sevice_account_json)
        )
        self._base_url = build_base_url(
            google_secops_project_id, google_secops_project_location, google_secops_instance_id
        )

    def update_sandbox_indicators(self, feeds: list[dict], task_uuid: str) -> None:
        """
        Initializes the process of updating indicators

        :param feeds: ANY.RUN Indicators
        :param task_uuid: ANY.RUN Sandbox analysis UUID
        """
        if not self._is_datatable_exists(Config.SANDBOX_DATATABLE):
            self._create_data_table(
                Config.SANDBOX_DATATABLE, build_sandbox_data_table_payload(Config.SANDBOX_DATATABLE)
            )

        if payload := build_sandbox_indicators_payload(feeds, task_uuid):
            self._load_indicators(Config.SANDBOX_DATATABLE, payload)

    def _is_datatable_exists(self, data_table_name: str) -> bool:
        """
        Checks if requested DataTable exists

        :param data_table_name: DataTable name
        :return: True if DataTable exists else None
        """
        url = f"{self._base_url}/dataTables/{data_table_name}"
        response = self._make_request("GET", url)

        if response.status == HTTPStatus.OK:
            self._logger.info(f"DataTable: {data_table_name} is already exists.")
            return True

        self._logger.info(f"DataTable: {data_table_name} is not found.")
        return False

    def _create_data_table(self, data_table_name: str, payload: dict) -> None:
        """
        Creates a new DataTable using SecOps API

        :param data_table_name: DataTable name
        :param payload: DataTable schema
        """
        self._logger.info(f"Create DataTable: {data_table_name}.")
        url = f"{self._base_url}/dataTables?dataTableId={data_table_name}"
        self._make_request("POST", url, payload)

    def _load_indicators(self, data_table_name: str, payload: dict) -> None:
        """
        Loads indicators into a DataTable

        :param data_table_name: DataTable name
        :param payload: DataTable schema
        """
        url = f"{self._base_url}/dataTables/{data_table_name}/dataTableRows:bulkCreate"
        self._make_request("POST", url, payload)

    def _make_request(self, method: str, url: str, payload: dict | None = None) -> Response:
        """
        Performs a request to the specified endpoint

        :param method: HTTP method
        :param url: Endpoint URL
        :param payload: Request payload
        :return: HTTP Response object
        """
        response = self._http_session.request(method, url, json=payload)
        return response
