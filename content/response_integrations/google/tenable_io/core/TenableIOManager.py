# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import re
import time
from typing import Any, Callable
from urllib.parse import urljoin

import requests
from .constants import (
    CANCELLED_STATUS,
    DEFAULT_ASSET_EXPORT_TIMEOUT,
    DEFAULT_CONTEXT_SCOPE,
    ENDPOINTS,
    ERROR_STATUS,
    FINISHED_STATUS,
)

from soar_sdk.SiemplifyAction import SiemplifyAction
from .TenableIOExceptions import (
    AssetExportException,
    ExportNotFinishedException,
    TenableIOException,
)
from .TenableIOParser import (
    Asset,
    EndpointVulnerability,
    PluginFamily,
    Policy,
    Scan,
    Scanner,
    TenableIOParser,
    Vulnerability,
    VulnerabilityDetails,
)

from .UtilsManager import filter_old_alerts, validate_response, write_pending_export


def normalize_string(text: str | None) -> str:
    """Normalize a string by replacing non-alphanumeric characters with underscores."""
    if not text:
        return "default"
    text = re.sub(r"[^a-zA-Z0-9]", "_", text.lower())
    result = re.sub(r"_+", "_", text).strip("_")
    return result if result else "default"


class TenableIOManager:

    def __init__(
        self,
        api_root: str,
        secret_key: str,
        access_key: str,
        verify_ssl: bool = False,
        siemplify_logger: Any | None = None,
        siemplify: SiemplifyAction | None = None,
    ) -> None:
        """Initializes a TenableIOManager object.

        Args:
            api_root (str): API root of the Tenable.io instance.
            secret_key (str): Secret Key for the API.
            access_key (str): Access Key for the API.
            verify_ssl (bool): If enabled, verifies the SSL certificate.
            siemplify_logger (Any | None): Siemplify logger object.
            siemplify (Any | None): Siemplify action object.
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.secret_key = secret_key
        self.access_key = access_key
        self.logger = siemplify_logger
        self.siemplify = siemplify
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = TenableIOParser()
        self.session.headers.update(
            {"x-apikeys": f"accessKey={self.access_key};secretKey={self.secret_key}"}
        )
        header_msg = "Integration/1.0 (Siemplify; TenableIO_Integration; Build/5.6"
        self.session.headers.update({"User-Agent": header_msg})

    def _get_full_url(self, url_id: str, **kwargs: Any) -> str:
        """Constructs a full URL from an endpoint ID and arguments.

        Args:
            url_id (str): The identifier for the endpoint URL.
            **kwargs (Any): Variables to format into the URL.

        Returns:
            str: The complete URL for the API request.
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _execute_request_with_retry(
        self,
        method: Callable,
        url_id: str,
        url_kwargs: dict | None = None,
        allow_duplicate_error: bool = False,
        validate: bool = True,
        **kwargs: Any,
    ) -> requests.Response:
        """Makes an HTTP request to the Tenable.io API with retry logic for 429s.

        Args:
            method (Callable): HTTP method callable (e.g., self.session.get).
            url_id (str): Identifier for the endpoint URL.
            url_kwargs (dict | None): Arguments to format into the URL.
            allow_duplicate_error (bool): Whether to return 429 duplicate error
                immediately.
            validate (bool): Whether to call validate_response on the response.
            **kwargs (Any): Additional arguments for requests.Session.request.

        Returns:
            requests.Response: The HTTP response object.
        """
        url = self._get_full_url(url_id, **(url_kwargs or {}))

        response = method(url, **kwargs)

        if response.status_code == 429:
            if (
                allow_duplicate_error
                and "duplicate export not allowed" in response.text.lower()
            ):
                return response

            wait_seconds = response.headers.get("retry-after")
            sleep_time = 5
            if wait_seconds:
                try:
                    sleep_time = min(int(wait_seconds), 60)
                except ValueError:
                    self.logger.warn(
                        f"Invalid retry-after header value: {wait_seconds}. "
                        f"Using fallback sleep of 5 seconds."
                    )

            self.logger.info(
                f"Rate limit hit (429). Sleeping for {sleep_time} "
                f"seconds based on retry-after header before retry..."
            )
            time.sleep(sleep_time)

            response = method(url, **kwargs)

        if validate:
            validate_response(response)
        return response

    def _get_identifier(self) -> str:
        env = (
            normalize_string(self.siemplify.environment)
            if self.siemplify
            else "DefaultEnv"
        )
        instance = (
            normalize_string(self.siemplify.integration_instance)
            if self.siemplify
            else "DefaultInstance"
        )
        return f"{env}_{instance}_TenableIO"

    def _get_cached_export_uuid(self) -> str | None:
        if not self.siemplify:
            return None
        identifier = self._get_identifier()
        export_uuid = self.siemplify.get_context_property(
            context_type=DEFAULT_CONTEXT_SCOPE,
            identifier=identifier,
            property_key="export_uuid",
        )
        timestamp = self.siemplify.get_context_property(
            context_type=DEFAULT_CONTEXT_SCOPE,
            identifier=identifier,
            property_key="export_timestamp",
        )

        if (
            export_uuid
            and timestamp
            and str(timestamp).isdigit()
            and time.time() - int(timestamp) < 3600
        ):
            self.logger.info(f"Using cached export UUID: {export_uuid}")
            return export_uuid
        return None

    def _set_cached_export_uuid(self, export_uuid: str) -> None:
        if not self.siemplify:
            return
        identifier = self._get_identifier()
        self.siemplify.set_context_property(
            context_type=DEFAULT_CONTEXT_SCOPE,
            identifier=identifier,
            property_key="export_uuid",
            property_value=export_uuid,
        )
        self.siemplify.set_context_property(
            context_type=DEFAULT_CONTEXT_SCOPE,
            identifier=identifier,
            property_key="export_timestamp",
            property_value=str(int(time.time())),
        )
        self.logger.info(f"Saved export_uuid to cache: {export_uuid}")

    def _clear_cached_export_uuid(self) -> None:
        if not self.siemplify:
            return
        identifier = self._get_identifier()
        self.siemplify.set_context_property(
            context_type=DEFAULT_CONTEXT_SCOPE,
            identifier=identifier,
            property_key="export_uuid",
            property_value="",
        )
        self.siemplify.set_context_property(
            context_type=DEFAULT_CONTEXT_SCOPE,
            identifier=identifier,
            property_key="export_timestamp",
            property_value="",
        )
        self.logger.info("Cleared cached export UUID.")

    def test_connectivity(self) -> None:
        """Tests connectivity to the Tenable.io API."""
        self._execute_request_with_retry(self.session.get, "ping")

    def get_all_assets(
        self, timeout_threshold: int = DEFAULT_ASSET_EXPORT_TIMEOUT
    ) -> list[Asset]:
        """Exports and retrieves all assets using the v2 export API.

        This method handles the entire export process: initiation, status
        checking, and chunk downloading.

        Args:
            timeout_threshold (int): Timeout for the asset export process in
                seconds.

        Returns:
            list[Asset]: A list of Asset objects.

        Raises:
            AssetExportException: If the export process times out or fails.
        """
        start_time = time.time()

        export_uuid = self._get_cached_export_uuid()

        if not export_uuid:
            self.logger.info("Initiating asset export.")
            export_uuid = self.initiate_assets_export()
            self.logger.info(f"Asset export initiated with UUID: {export_uuid}")
            self._set_cached_export_uuid(export_uuid)

        try:
            while time.time() - start_time <= timeout_threshold:
                status = self.get_assets_export_status(export_uuid)
                self.logger.info(f"Current export status: {status.get('status')}")

                if status.get("status") == FINISHED_STATUS:
                    self.logger.info("Asset export finished. Downloading chunks.")
                    all_assets = []
                    for chunk_id in status.get("chunks_available", []):
                        self.logger.info(f"Downloading chunk {chunk_id}.")
                        chunk_data = self.download_asset_chunk(export_uuid, chunk_id)
                        all_assets.extend(chunk_data)
                    self.logger.info(
                        f"Successfully downloaded {len(all_assets)} assets."
                    )
                    return self.parser.build_asset_objects({"assets": all_assets})

                if status.get("status") in [CANCELLED_STATUS, ERROR_STATUS]:
                    self._clear_cached_export_uuid()
                    raise AssetExportException(
                        f"Asset export failed with status: {status.get('status')}."
                    )

                time.sleep(3)  # Wait 3 seconds before checking status again

            self._clear_cached_export_uuid()
            raise AssetExportException(
                f"Asset export process timed out after {timeout_threshold} seconds."
            )
        except Exception:
            self._clear_cached_export_uuid()
            raise

    def initiate_assets_export(self) -> str:
        """Initiates an export of all assets.

        Returns:
            str: The UUID of the export job.
        """
        payload = {"chunk_size": 1000}
        response = self._execute_request_with_retry(
            self.session.post,
            "initiate_assets_export",
            json=payload,
            allow_duplicate_error=True,
        )

        if (
            response.status_code == 429
            and "duplicate export not allowed" in response.text.lower()
        ):
            # NOTE: Extracting job_uuid from error text is fragile but necessary
            # if not provided in structured response.
            match = re.search(r"job_uuid=([a-fA-F0-9-]+)", response.text)
            if match:
                export_uuid = match.group(1)
                self.logger.info(f"Extracted job_uuid from 429 response: {export_uuid}")

                self._set_cached_export_uuid(export_uuid)

                return export_uuid

            self.logger.error("Could not extract job_uuid from 429 response.")
            validate_response(response)

        export_uuid = response.json().get("export_uuid")
        if not export_uuid:
            raise AssetExportException(
                "Failed to extract export_uuid from Tenable.io response."
            )
        return export_uuid

    def get_assets_export_status(self, export_uuid: str) -> dict:
        """Checks the status of an ongoing asset export.

        Args:
            export_uuid (str): The UUID of the export job.

        Returns:
            dict: The status JSON object.
        """
        response = self._execute_request_with_retry(
            self.session.get,
            "get_assets_export_status",
            url_kwargs={"export_uuid": export_uuid},
        )
        return response.json()

    def download_asset_chunk(self, export_uuid: str, chunk_id: int) -> list[dict]:
        """Downloads a specific chunk of an asset export.

        Args:
            export_uuid (str): The UUID of the export job.
            chunk_id (int): The ID of the chunk to download.

        Returns:
            list[dict]: A list of asset data dictionaries.
        """
        response = self._execute_request_with_retry(
            self.session.get,
            "download_assets_chunk",
            url_kwargs={"export_uuid": export_uuid, "chunk_id": chunk_id},
        )
        return response.json()

    def get_asset(self, asset_id: str) -> Asset:
        """Gets details for a specific asset.

        Args:
            asset_id (str): The UUID of the asset.

        Returns:
            Asset: An Asset object.
        """
        response = self._execute_request_with_retry(
            self.session.get, "asset", url_kwargs={"id": asset_id}
        )
        return self.parser.build_asset_object(response.json())

    def list_plugin_families(self) -> list[PluginFamily]:
        """Lists all plugin families.

        Returns:
            list[PluginFamily]: A list of PluginFamily objects.
        """
        response = self._execute_request_with_retry(
            self.session.get, "list_plugin_families", validate=False
        )
        validate_response(response, "Unable to list plugin families")
        return self.parser.build_plugin_families_list(response.json())

    def list_policies(self) -> list[Policy]:
        """Lists all policies.

        Returns:
            list[Policy]: A list of Policy objects.
        """
        response = self._execute_request_with_retry(
            self.session.get, "list_policies", validate=False
        )
        validate_response(response, "Unable to list policies")
        return self.parser.build_policies_list(response.json())

    def list_scanners(self) -> list[Scanner]:
        """Lists all scanners.

        Returns:
            list[Scanner]: A list of Scanner objects.
        """
        response = self._execute_request_with_retry(
            self.session.get, "list_scanners", validate=False
        )
        validate_response(response, "Unable to list scanners")
        return self.parser.build_scanners_list(response.json())

    def initiate_export(
        self,
        statuses: list[str],
        severities: list[str],
        start_timestamp: int,
        plugin_families: list[str],
    ) -> str:
        """Initiates a vulnerability export.

        Args:
            statuses (list[str]): List of statuses to filter by.
            severities (list[str]): List of severities to filter by.
            start_timestamp (int): The Unix timestamp from which to fetch.
            plugin_families (list[str]): List of plugin families to filter by.

        Returns:
            str: The UUID of the export job.
        """
        payload = {
            "filters": {
                "severity": severities,
                "plugin_family": plugin_families,
                "since": int(str(start_timestamp)[:-3]),
                "state": statuses,
            }
        }
        response = self._execute_request_with_retry(
            self.session.post, "initiate_export", json=payload, validate=False
        )
        validate_response(response, "Unable to initiate export")
        return response.json().get("export_uuid")

    def get_export_status(self, siemplify: SiemplifyAction, export_uuid: str) -> dict:
        """Gets the status of a vulnerability export.

        Args:
            siemplify (SiemplifyAction): The Siemplify action object.
            export_uuid (str): The UUID of the export job.

        Returns:
            dict: The export status data if finished.

        Raises:
            ExportNotFinishedException: If the export is not finished,
                cancelled, or has an error.
        """
        response = self._execute_request_with_retry(
            self.session.get,
            "get_export_status",
            url_kwargs={"export_id": export_uuid},
            validate=False,
        )
        validate_response(response, "Unable to check export status")
        export_data = response.json()
        export_status = export_data.get("status")

        if export_status == FINISHED_STATUS:
            return export_data
        elif export_status in [CANCELLED_STATUS, ERROR_STATUS]:
            raise ExportNotFinishedException(
                f"Export {export_uuid} status is {export_status}. "
                f"Connector will stop the iteration and skip the export."
            )
        else:
            write_pending_export(siemplify, export_data)
            raise ExportNotFinishedException(
                f"Export {export_uuid} status is {export_status}. "
                f"Connector will stop the iteration and save the export data."
            )

    def get_export_chunk_data(
        self, existing_ids: list[str], export_uuid: str, chunk_id: int
    ) -> list[Vulnerability]:
        """Gets a chunk of data from a vulnerability export.

        Args:
            existing_ids (list[str]): A list of existing alert IDs to filter out.
            export_uuid (str): The UUID of the export job.
            chunk_id (int): The ID of the chunk to download.

        Returns:
            list[Vulnerability]: A sorted list of new Vulnerability objects.
        """
        response = self._execute_request_with_retry(
            self.session.get,
            "export_chunk_data",
            url_kwargs={"export_id": export_uuid, "chunk_id": chunk_id},
            validate=False,
        )
        validate_response(response, "Unable to get vulnerabilities")
        vulnerabilities = self.parser.build_vulnerabilities_list(response.json())
        filtered_alerts = filter_old_alerts(
            logger=self.logger, alerts=vulnerabilities, existing_ids=existing_ids
        )
        return sorted(filtered_alerts, key=lambda vuln: vuln.last_found)

    def get_vulnerability_details(self, plugin_id: str) -> VulnerabilityDetails:
        """Gets details for a specific vulnerability plugin.

        Args:
            plugin_id (str): The ID of the plugin.

        Returns:
            VulnerabilityDetails: A VulnerabilityDetails object.
        """
        response = self._execute_request_with_retry(
            self.session.get,
            "get_vulnerabilities_details",
            url_kwargs={"plugin_id": plugin_id},
        )
        return self.parser.build_vulnerability_details_object(
            response.json(), plugin_id
        )

    def get_endpoint_vulnerabilities(
        self, asset_id: str, severities: list[str], limit: int
    ) -> list[EndpointVulnerability]:
        """Lists vulnerabilities for a specific endpoint.

        Args:
            asset_id (str): The UUID of the asset.
            severities (list[str]): A list of severities to filter by.
            limit (int): The maximum number of vulnerabilities to return.

        Returns:
            list[EndpointVulnerability]: A list of EndpointVulnerability objects.

        Raises:
            TenableIOException: If a non-5xx API error occurs.
            Exception: If a 5xx API error occurs.
        """
        severity_filter = self.build_severity_filter(severities)
        response = self._execute_request_with_retry(
            self.session.get,
            "list_vulnerabilities",
            url_kwargs={"asset_id": asset_id, "query_string": severity_filter},
            validate=False,
        )
        try:
            validate_response(response)
        except Exception as e:
            raise TenableIOException(str(e)) from e
        return self.parser.build_endpoint_vulnerabilities_list(response.json())[:limit]

    def build_severity_filter(self, severities: list[str]) -> str:
        """Creates a severity filter string for API queries.

        Args:
            severities (list[str]): A list of severities.

        Returns:
            str: A URL-encoded filter string.
        """
        filters = [
            (
                f"filter.{i}.filter=severity&filter.{i}.quality=eq&filter.{i}."
                f"value={value.lower()}"
            )
            for i, value in enumerate(severities)
        ]
        return "&filter.search_type=or&".join(filters)

    def create_scan(
        self,
        policy_uuid: str,
        scan_name: str,
        ip_address: str,
        emails: str,
        scanner_id: int,
    ) -> int | None:
        """Creates a new scan.

        Args:
            policy_uuid (str): The UUID of the policy to use.
            scan_name (str): The name of the scan.
            ip_address (str): The target IP address(es).
            emails (str): A CSV of email addresses for notifications.
            scanner_id (int): The ID of the scanner to use.

        Returns:
            int | None: The ID of the created scan, or None if creation fails.
        """
        payload = {
            "uuid": policy_uuid,
            "settings": {
                "name": scan_name,
                "enabled": True,
                "text_targets": ip_address,
                "launch": "ON_DEMAND",
                "emails": emails or "",
            },
        }
        if scanner_id is not None:
            payload["settings"]["scanner_id"] = scanner_id
        response = self._execute_request_with_retry(
            self.session.post, "create_scan", json=payload
        )
        return response.json().get("scan", {}).get("id")

    def launch_scan(self, scan_id: int) -> None:
        """Launches a scan.

        Args:
            scan_id (int): The ID of the scan to launch.
        """
        self._execute_request_with_retry(
            self.session.post, "launch_scan", url_kwargs={"scan_id": scan_id}
        )

    def check_scan_status(self, scan_id: int) -> str:
        """Checks the status of a scan.

        Args:
            scan_id (int): The ID of the scan.

        Returns:
            str: The current status of the scan.
        """
        response = self._execute_request_with_retry(
            self.session.get, "check_scan_status", url_kwargs={"scan_id": scan_id}
        )
        return response.json().get("status", "")

    def get_scan_results(self, scan_id: int) -> Scan:
        """Gets the results of a completed scan.

        Args:
            scan_id (int): The ID of the scan.

        Returns:
            Scan: A Scan object containing the results.
        """
        response = self._execute_request_with_retry(
            self.session.get, "get_scan_results", url_kwargs={"scan_id": scan_id}
        )
        return self.parser.build_scan_object(response.json())
