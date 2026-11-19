from __future__ import annotations

from urllib.parse import urljoin

import requests

from soar_sdk.SiemplifyLogger import SiemplifyLogger

from microsoft_intune.core.exceptions import MicrosoftIntuneBadRequestError, MicrosoftIntuneManagerError
from microsoft_intune.core.constants import (
    API_BAD_REQUEST,
    API_SERVER_ERROR,
    API_UNAUTHORIZED_ERROR,
    ENDPOINTS,
    GENERATE_TOKEN_PAYLOAD_FROM_SECRET,
    MAX_RECORDS_TO_RETURN_DEFAULT_VALUE,
    FILTER_KEY_DEFAULT_VALUE,
    FILTER_LOGIC_DEFAULT_VALUE,
    FILTER_VALUE_DEFAULT_VALUE,
)
from microsoft_intune.core.datamodels import GetManageDeviceData, ListManagedDevices
from microsoft_intune.core import MicrosoftIntuneParser as parser
from microsoft_intune.core.UtilsManager import filter_list_data


class MicrosoftIntuneManager:
    """
    Microsoft Intune Integration API interaction class
    """

    def __init__(
        self,
        azure_ad_endpoint: str,
        microsoft_graph_endpoint: str,
        client_id: str,
        client_secret_value: str,
        azure_ad_id: str,
        verify_ssl: bool,
        logger: SiemplifyLogger | None = None,
    ) -> None:
        """Class constructor

        Args:
            azure_ad_endpoint: Azure endpoint of the MS Intune instance.
            microsoft_graph_endpoint: MS graph endpoint of the MS Intune account
            client_id: Client ID of the MS Intune account.
            client_secret_value: Client Secret value of the MS Intune account.
            azure_ad_id: Azure ad id of the MS Intune account.
            verify_ssl: If enabled, verify the SSL certificate for the
            connection to the Microsoft Intune server is valid.
        """
        self.azure_ad_endpoint = (
            azure_ad_endpoint[:-1]
            if azure_ad_endpoint.endswith("/")
            else azure_ad_endpoint
        )
        self.microsoft_graph_endpoint = microsoft_graph_endpoint
        self.client_id = client_id
        self.client_secret_value = client_secret_value
        self.azure_ad_id = azure_ad_id
        self.verify_ssl = verify_ssl

        self.logger = logger

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {"Authorization": f"Bearer {self.generate_token()}"}
        )

    def _get_full_url(self, url_id: str, **kwargs: str | int) -> str:
        """Get full url from url identifier.

        Args:
            url_id: The id of url.
            **kwargs: Variables passed for string formatting.

        Returns:
            The full url
        """
        return urljoin(self.azure_ad_endpoint, ENDPOINTS[url_id].format(**kwargs))

    def generate_token(self) -> str:
        """Generate Token for MS Intune.

        Returns:
            str: Access token
        """
        payload = GENERATE_TOKEN_PAYLOAD_FROM_SECRET
        payload["client_id"] = self.client_id
        payload["client_secret"] = self.client_secret_value
        url = self._get_full_url(
            "ping", base_url=self.azure_ad_endpoint, azure_ad_id=self.azure_ad_id
        )
        response = self.session.post(url, data=payload)
        self.validate_response(response)
        return response.json().get("access_token")

    def get_managed_device(self, host_id: str) -> GetManageDeviceData:
        """Get managed device in MS Intune

        Args:
            host_id: Host ID for get device

        Returns:
            None
        """
        url = self._get_full_url(
            "get_managed_device",
            base_url=self.microsoft_graph_endpoint,
            host_id=host_id.strip(),
        )
        response = self.session.get(url)
        self.validate_response(response)
        return parser.build_get_managed_device_obj(response.json())

    def list_managed_devices(
        self,
        filter_key: str,
        filter_logic: str,
        filter_value: str,
        max_records_to_return: int,
    ) -> ListManagedDevices:
        """List managed devices in MS Intune

        Args:
            filter_key: Key needs to be used to filter managed devices
            filter_logic: Filtering logic is working based on the value
                provided in the “Filter Key” parameter
            filter_value: Specify what value should be used in the filter
            max_records_to_return: Specify how many records to return

        Returns:
            ListManagedDevices Obj
        """
        url = self._get_full_url(
            "list_managed_devices",
            base_url=self.microsoft_graph_endpoint,
            page_size=MAX_RECORDS_TO_RETURN_DEFAULT_VALUE,
        )
        response = self._paginate_results_with_filter(
            url=url,
            filter_key=filter_key,
            filter_logic=filter_logic,
            filter_value=filter_value,
            max_records_to_return=max_records_to_return,
        )

        if self.logger is not None:
            self.logger.info(f'Fetched {response["@odata.count"]} results')

        return parser.build_list_managed_devices_obj(raw_data=response)

    def list_all_managed_devices(
        self, host_ids: list = None, host_names: list = None
    ) -> ListManagedDevices:
        """List all managed devices in MS Intune
        Args:
            host_ids: Host IDs for verify devices
            host_names: Host Names for verify devices
        Returns:
            ListManagedDevices Obj
        """
        url = self._get_full_url(
            "list_managed_devices",
            base_url=self.microsoft_graph_endpoint,
            page_size=MAX_RECORDS_TO_RETURN_DEFAULT_VALUE,
        )
        response = self._get_host_details_by_id_or_name(
            url, host_ids=host_ids, host_names=host_names
        )

        if self.logger is not None:
            self.logger.info(f'Fetched {response["@odata.count"]} results')

        return parser.build_list_all_managed_devices_obj(response)

    def _paginate_results_with_filter(
        self,
        url: str,
        method: str = "GET",
        filter_key: str = FILTER_KEY_DEFAULT_VALUE,
        filter_logic: str = FILTER_LOGIC_DEFAULT_VALUE,
        filter_value: str = FILTER_VALUE_DEFAULT_VALUE,
        max_records_to_return: int | None = None,
    ) -> dict:
        """Request using pagination with filter

        Args:
            url: The url to send request to
            method: The method of the request (GET, POST, PUT, DELETE, PATCH)
            filter_key: Key needs to be used to filter managed devices
            filter_logic: Filtering logic is working based on the value
                provided in the “Filter Key” parameter
            filter_value: Specify what value should be used in the filter
            max_records_to_returns: Specify how many records to return

        Returns:
            The results of the response
        """
        results = {}
        filter_response = []
        while url:
            response = self.session.request(method, url)
            self.validate_response(response)

            json_result = response.json()
            url = json_result.get("@odata.nextLink")
            filter_response.extend(
                filter_list_data(
                    json_result.get("value", []), filter_key, filter_logic, filter_value
                )
            )
            filter_response = filter_response[:max_records_to_return]
            results = {
                "@odata.count": len(filter_response),
                "@odata.context": json_result["@odata.context"],
                "value": filter_response,
            }
            if len(filter_response) == max_records_to_return:
                return results

        return results

    def _get_host_details_by_id_or_name(
        self,
        url: str,
        method: str = "GET",
        host_ids: list = None,
        host_names: list = None,
    ) -> dict:
        """Retrieves a paginated list of host details from an API, optionally
        filtering by host IDs or host names.

        This function makes API calls to the given URL and handles pagination
        to collect all host details.

        It can accept filters for specific host IDs or host names to retrieve
        only matching records.

        The pagination continues until all relevant data is gathered or until
        the specified filters are fully matched.

        Args:
            url: The url to send request to
            host_ids: Host IDs for verify devices
            host_names: Host Names for verify devices
            method: The method of the request (GET, POST, PUT, DELETE, PATCH)

        Returns:
            The results of the response
        """
        if host_ids is None:
            host_ids = []
        if host_names is None:
            host_names = []

        results = []
        json_result = {}
        while url:
            response = self.session.request(method, url)
            self.validate_response(response)

            json_result = response.json()
            url = json_result.get("@odata.nextLink")
            results.extend(json_result.get("value", []))

            if host_ids:
                devices = [device.get("id", "") for device in results]
                if set(host_ids) <= set(devices):
                    break
            else:
                devices = [device.get("deviceName", "") for device in results]
                if set(host_names) <= set(devices):
                    break

        return {
            "@odata.count": len(results),
            "@odata.context": json_result["@odata.context"],
            "value": results,
        }

    def locate_managed_device(self, host_id: str) -> None:
        """Locate managed device in MS Intune

        Args:
            host_id: Host ID for locate device

        Returns:
            None
        """
        url = self._get_full_url(
            "locate_managed_device",
            base_url=self.microsoft_graph_endpoint,
            host_id=host_id.strip(),
        )
        response = self.session.post(url)
        self.validate_response(response)

    def reset_managed_device_passcode(self, host_id: str) -> None:
        """Reset managed device in MS Intune

        Args:
            host_id: Host ID for reset device

        Returns:
            None
        """
        url = self._get_full_url(
            "reset_managed_device",
            base_url=self.microsoft_graph_endpoint,
            host_id=host_id.strip(),
        )
        response = self.session.post(url)
        self.validate_response(response)

    def remote_lock_managed_device(self, host_id: str) -> None:
        """Remote Lock Managed Device in MS Intune

        Args:
            host_id: Host ID for remote lock

        Returns:
            bool
        """
        url = self._get_full_url(
            "remote_lock_managed_device",
            base_url=self.microsoft_graph_endpoint,
            host_id=host_id.strip(),
        )
        response = self.session.post(url)
        self.validate_response(response)

    def validate_response(
        self, response: requests.Response, error_msg: str = "An error occurred"
    ) -> None:
        """Validates response

        Args:
            response: The response to validate
            error_msg: Default message to display on error
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            if (
                response.status_code == API_BAD_REQUEST
                or response.status_code == API_SERVER_ERROR
            ):
                raise MicrosoftIntuneBadRequestError(
                    self.get_api_error_message(error)
                ) from error

            if response.status_code == API_UNAUTHORIZED_ERROR:
                raise MicrosoftIntuneManagerError(error)

            if response.json()["message"] == error_msg:
                return

            raise MicrosoftIntuneManagerError(
                self.get_api_error_message(error)
            ) from error

    def get_api_error_message(self, exception) -> str:
        """Get API error message.

        Args:
            exception: {Exception} The api error

        Returns:
            {str} error message
        """
        try:
            return parser.extract_error_message(exception.response.json())

        except Exception:
            if exception.response.content.decode():
                return exception.response.content.decode()

            return str(exception)

    def sync_managed_device(self, host_id: str) -> None:
        """Initiate sync task for intune managed device

        Args:
            host_id: Host id for which the sync task is initiated

        Returns:
            bool
        """
        url = self._get_full_url(
            "sync_managed_device",
            base_url=self.microsoft_graph_endpoint,
            host_id=host_id,
        )
        response = self.session.post(url)
        self.validate_response(response)

    def wipe_managed_device(
        self,
        host_id: str,
        keep_enrollment_data: bool,
        keep_user_data: bool,
        persist_esim_data_plan: bool,
        mac_os_unlock_code: str,
    ) -> None:
        """Initiate wipe task for intune managed device

        Args:
            host_id: Host id for which the wipe task is initiated
            keep_enrollment_data: Check to keep enrollment data on the device
            keep_user_data: Check to keep user data on the device.
            persist_esim_data_plan:
                Check to persist esim data plan for the device
            mac_os_unlock_code: Applicable macOS unlock code.

        Returns:
            bool
        """
        url = self._get_full_url(
            "wipe_managed_device",
            base_url=self.microsoft_graph_endpoint,
            host_id=host_id,
        )
        payload = {
            "keepEnrollmentData": keep_enrollment_data,
            "keepUserData": keep_user_data,
            "macOsUnlockCode": mac_os_unlock_code,
            "persistEsimDataPlan": persist_esim_data_plan,
        }
        response = self.session.post(url, data=payload)
        self.validate_response(response)
