from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

from anyrun.connectors import FeedsConnector
from anyrun.iterators import FeedsIterator
from google.auth.transport import Response, requests
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.rest.auth import build_credentials_from_sa

from ..core.config import Config
from ..core.utils import (
    build_base_url,
    build_taxii_data_table_payload,
    build_taxii_indicators_payload,
    setup_job_proxy,
)


class DataTableManager:
    """Provides methods to manage IOCs and interact with DataTables"""

    def __init__(self, siemplify: SiemplifyJob) -> None:
        token = extract_configuration_param(
            siemplify,
            Config.INTEGRATION_NAME,
            param_name="ANYRUN TI Feeds Basic token",
            is_mandatory=True,
        )

        google_secops_project_id = extract_configuration_param(
            siemplify, Config.INTEGRATION_NAME, param_name="Project ID", is_mandatory=True
        )

        google_secops_project_location = extract_configuration_param(
            siemplify, Config.INTEGRATION_NAME, param_name="Project location", is_mandatory=True
        )

        google_secops_instance_id = extract_configuration_param(
            siemplify, Config.INTEGRATION_NAME, param_name="Instance ID", is_mandatory=True
        )

        google_secops_sevice_account_json = json.loads(
            extract_configuration_param(
                siemplify,
                Config.INTEGRATION_NAME,
                param_name="Google service account",
                is_mandatory=True,
            )
        )

        self._siemplify = siemplify
        self._token = token
        self._logger = siemplify.LOGGER
        self._http_session = requests.AuthorizedSession(
            build_credentials_from_sa(google_secops_sevice_account_json)
        )
        self._base_url = build_base_url(
            google_secops_project_id, google_secops_project_location, google_secops_instance_id
        )

    def update_taxii_indicators(self, feed_fetch_depth: int, verify_ssl: bool) -> None:
        """
        Initializes the process of updating indicators

        :param feed_fetch_depth: Feed fetch depth
        """
        with FeedsConnector(
            api_key=self._token,
            integration=Config.VERSION,
            proxy=setup_job_proxy(self._siemplify),
            verify_ssl=verify_ssl,
        ) as connector:
            for collection, data_table_name in Config.TAXII_DATATABLES.items():
                if self._is_datatable_exists(data_table_name):
                    self._delete_data_table(data_table_name)

                self._create_data_table(
                    data_table_name, build_taxii_data_table_payload(data_table_name)
                )
                self._retreive_indicators(connector, collection, data_table_name, feed_fetch_depth)

    def _is_datatable_exists(
        self,
        data_table_name: str,
    ) -> bool:
        """
        Checks if requested DataTable exists

        :param data_table_name: DataTable name
        :return: True if DataTable exists else None
        """
        url = f"{self._base_url}/dataTables/{data_table_name}"
        response = self._make_request("GET", url)

        if response.status_code == HTTPStatus.OK:
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

    def _delete_data_table(self, data_table_name: str) -> None:
        """
        Deletes DataTable using SecOps API

        :param data_table_name: DataTable name
        """
        self._logger.info(f"Delete DataTable: {data_table_name}.")
        url = f"{self._base_url}/dataTables/{data_table_name}?force=true"
        self._make_request("DELETE", url)

    def _retreive_indicators(
        self,
        connector: FeedsConnector,
        collection: str,
        data_table_name: str,
        feed_fetch_depth: int,
    ) -> None:
        """
        Retrieves IOCs using ANY.RUN TAXII/STIX endpoint

        :param connector: ANY.RUN Feeds connector
        :param collection: TAXII/STIX collection name
        :param data_table_name: DataTable name
        :param feed_fetch_depth: Feed fetch depth
        """
        for feeds in FeedsIterator.taxii_stix(
            connector,
            collection=collection,
            match_type="indicator",
            match_version="all",
            chunk_size=1000,
            limit=10000,
            modified_after=(datetime.now(UTC) - timedelta(days=feed_fetch_depth)).strftime(
                Config.DATE_TIME_FORMAT
            ),
        ):
            if payload := build_taxii_indicators_payload(feeds):
                self._load_indicators(data_table_name, payload)

    def _load_indicators(self, data_table_name: str, payload: dict | list[dict[str, str]]) -> None:
        """
        Loads indicators into a DataTable

        :param data_table_name: DataTable name
        :param payload: IOCs payload
        """
        url = f"{self._base_url}/dataTables/{data_table_name}/dataTableRows:bulkCreate"
        self._make_request("POST", url, payload)

    def _make_request(
        self, method: str, url: str, payload: dict | dict | list[dict[str, str]] | None = None
    ) -> Response:
        """
        Performs a request to the specified endpoint

        :param method: HTTP method
        :param url: Endpoint URL
        :param payload: Request payload
        :return: HTTP Response object
        """
        response = self._http_session.request(method, url, json=payload)
        return response
