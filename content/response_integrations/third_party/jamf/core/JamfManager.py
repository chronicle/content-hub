from __future__ import annotations

import time
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import requests

from .constants import API_ENDPOINTS, USER_AGENT
from .exceptions import JamfError, JamfInvalidParameterError

if TYPE_CHECKING:
    pass


class JamfManager:
    """
    Jamf Pro API Manager for handling authentication and API operations
    """

    def __init__(
        self,
        api_root: str,
        client_api_id: str,
        client_api_secret: str,
        verify_ssl: bool = True,
        logger=None,
    ):
        """
        Initialize Jamf Manager

        Args:
            api_root: Jamf Pro server URL (e.g., https://yourserver.jamfcloud.com)
            client_api_id: API client ID
            client_api_secret: API client secret
            verify_ssl: Whether to verify SSL certificates
            logger: Logger instance
        """
        self.api_root = api_root.rstrip("/")
        self.client_api_id = client_api_id
        self.client_api_secret = client_api_secret
        self.verify_ssl = verify_ssl
        self.logger = logger
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.access_token = None
        self.token_expires_in = None
        self.token_expiration_epoch = 0

        # Set default headers
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        })

    def _get_full_url(self, endpoint: str) -> str:
        """
        Construct full URL for API endpoint

        Args:
            endpoint: API endpoint path

        Returns:
            Full URL string
        """
        return urljoin(self.api_root, endpoint.lstrip("/"))

    def _log(self, level: str, message: str):
        """Helper method for logging"""
        if self.logger:
            getattr(self.logger, level.lower())(message)

    def get_access_token(self) -> str:
        """
        Get access token from Jamf Pro API using client credentials

        Returns:
            Access token string

        Raises:
            JamfError: If authentication fails
        """
        try:
            auth_url = self._get_full_url(API_ENDPOINTS["auth"])

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            data = {
                "client_id": self.client_api_id,
                "grant_type": "client_credentials",
                "client_secret": self.client_api_secret,
            }

            self._log("info", f"Getting access token from Jamf Pro at: {auth_url}")
            self._log("info", f"Authenticating with Jamf Pro at: {auth_url}")
            self._log("info", f"Client API ID: {self.client_api_id}")

            response = self.session.post(auth_url, headers=headers, data=data, timeout=30)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.token_expires_in = token_data.get("expires_in")

                # Calculate token expiration epoch (subtract 1 second for safety)
                current_epoch = int(time.time())
                self.token_expiration_epoch = current_epoch + self.token_expires_in - 1

                # Update session headers with bearer token
                self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

                self._log(
                    "info",
                    f"Successfully obtained access token, expires at epoch: "
                    f"{self.token_expiration_epoch}",
                )
                return self.access_token
            else:
                error_msg = (
                    f"Failed to get access token. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error getting access token: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)

    def check_token_expiration(self) -> bool:
        """
        Check if current token is valid and get new one if needed

        Returns:
            True if valid token is available
        """
        current_epoch = int(time.time())

        if self.token_expiration_epoch >= current_epoch and self.access_token:
            self._log("info", f"Token valid until epoch time: {self.token_expiration_epoch}")
            return True
        else:
            self._log("info", "No valid token available, getting new token")
            self.get_access_token()
            return True

    def invalidate_token(self) -> bool:
        """
        Invalidate the current access token

        Returns:
            True if token was successfully invalidated
        """
        if not self.access_token:
            self._log("info", "No token to invalidate")
            return True

        try:
            invalidate_url = self._get_full_url(API_ENDPOINTS["invalidate_token"])

            response = self.session.post(invalidate_url, timeout=30)

            if response.status_code == 204:
                self._log("info", "Token successfully invalidated")
                self.access_token = None
                self.token_expiration_epoch = 0
                # Remove authorization header
                if "Authorization" in self.session.headers:
                    del self.session.headers["Authorization"]
                return True
            elif response.status_code == 401:
                self._log("info", "Token already invalid")
                self.access_token = None
                self.token_expiration_epoch = 0
                return True
            else:
                self._log(
                    "error", f"Unknown error invalidating token. Status: {response.status_code}"
                )
                return False

        except Exception as e:
            self._log("error", f"Error invalidating token: {str(e)}")
            return False

    def test_connectivity(self) -> bool:
        """
        Test connectivity to Jamf Pro API

        Returns:
            True if connection successful

        Raises:
            JamfError: If connection fails
        """
        try:
            # Ensure we have a valid token
            self.check_token_expiration()

            # Test with Jamf Pro version endpoint
            test_url = self._get_full_url(API_ENDPOINTS["jamf_pro_version"])

            self._log("info", f"Testing connectivity to: {test_url}")

            response = self.session.get(test_url, timeout=30)

            if response.status_code == 200:
                version_info = response.json()
                version = version_info.get("version", "Unknown")
                self._log("info", f"Successfully connected to Jamf Pro version: {version}")
                return True
            else:
                error_msg = (
                    f"Connectivity test failed with status {response.status_code}: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error during connectivity test: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)

    def list_computer_groups(self) -> list:
        """
        List all computer groups from Jamf Pro

        Returns:
            List of computer groups

        Raises:
            JamfError: If request fails
        """
        try:
            # Ensure we have a valid token
            self.check_token_expiration()

            groups_url = self._get_full_url(API_ENDPOINTS["computer_groups"])

            self._log("info", f"Retrieving computer groups from: {groups_url}")

            response = self.session.get(groups_url, timeout=30)

            if response.status_code == 200:
                groups_data = response.json()

                # Handle both possible response formats
                if isinstance(groups_data, list):
                    # API returns a direct list of groups
                    groups = groups_data
                    self._log(
                        "info", f"API returned direct list with {len(groups)} groups: {groups}"
                    )
                else:
                    # Unexpected format
                    groups = []
                    self._log(
                        "info",
                        f"API returned unexpected format: {type(groups_data)} - {groups_data}",
                    )

                self._log("info", f"Successfully retrieved {len(groups)} computer groups")
                return groups
            else:
                error_msg = (
                    f"Failed to retrieve computer groups. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error retrieving computer groups: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)

    def get_device_info(self, device_id: str) -> dict:
        """
        Get detailed device information from Jamf Pro

        Args:
            device_id: The ID of the device to retrieve information for

        Returns:
            Dictionary containing device information

        Raises:
            JamfError: If request fails
        """
        try:
            # Ensure we have a valid token
            self.check_token_expiration()

            # Format the URL with the device ID
            device_url = self._get_full_url(
                API_ENDPOINTS["computer_inventory_detail"].format(id=device_id)
            )

            self._log("info", f"Retrieving device information from: {device_url}")

            response = self.session.get(device_url, timeout=30)

            if response.status_code == 200:
                device_data = response.json()

                # Clean the data to prevent JSON parsing issues in widgets
                device_data = self._clean_string_for_json(device_data)

                self._log("info", f"Successfully retrieved device information for ID: {device_id}")
                return device_data
            elif response.status_code == 404:
                error_msg = f"Device with ID {device_id} not found"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            else:
                error_msg = (
                    f"Failed to retrieve device information. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error retrieving device information: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)

    def get_device_group_membership(self, group_id: str) -> dict:
        """
        Get the membership of a Computer Group from Jamf Pro

        Args:
            group_id: The ID of the group to retrieve membership for

        Returns:
            Dictionary containing group membership information

        Raises:
            JamfError: If request fails
        """
        try:
            # Ensure we have a valid token
            self.check_token_expiration()

            # Format the URL with the group ID
            membership_url = self._get_full_url(
                API_ENDPOINTS["device_group_membership"].format(id=group_id)
            )

            self._log("info", f"Retrieving device group membership from: {membership_url}")

            response = self.session.get(membership_url, timeout=30)

            if response.status_code == 200:
                membership_data = response.json()
                self._log(
                    "info", f"Successfully retrieved device group membership for ID: {group_id}"
                )
                return membership_data
            elif response.status_code == 404:
                error_msg = f"Device group with ID {group_id} not found"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            else:
                error_msg = (
                    f"Failed to retrieve device group membership. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error retrieving device group membership: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)

    def get_computer_inventory(self, page=0, page_size=100, sort=None, filter=None, section=None):
        """
        Retrieve paginated Computer Inventory records from Jamf Pro.

        Args:
            page (int): Page number to retrieve (default: 0)
            page_size (int): Number of records per page (default: 100, max: 2000)
            sort (str): Sort criteria (comma-separated list of field:direction pairs)
            filter (str): Filter criteria using Jamf Pro API filter syntax
            section (str): Comma-separated list of sections to include in response

        Returns:
            dict: Computer inventory data including results and pagination info

        Raises:
            JamfError: If the API request fails
        """
        try:
            self._log("info", f"Retrieving computer inventory - Page: {page}, Size: {page_size}")

            # Validate parameters
            if page < 0:
                raise JamfInvalidParameterError("Page number must be 0 or greater")
            if page_size < 1 or page_size > 2000:
                raise JamfInvalidParameterError("Page size must be between 1 and 2000")

            # Ensure we have a valid token
            self.check_token_expiration()

            # Build query parameters
            params = {"page": page, "page-size": page_size}

            if sort:
                params["sort"] = sort
            if filter:
                params["filter"] = filter
            if section:
                params["section"] = section

            inventory_url = self._get_full_url(API_ENDPOINTS["computers_inventory"])

            self._log(
                "info", f"Retrieving computer inventory from: {inventory_url} with params: {params}"
            )

            # Use params directly - requests will handle the URL encoding
            response = self.session.get(inventory_url, params=params, timeout=30)

            if response.status_code == 200:
                inventory_data = response.json()

                # Clean the data to prevent JSON parsing issues in widgets
                inventory_data = self._clean_string_for_json(inventory_data)

                results = inventory_data.get("results", [])
                total_count = inventory_data.get("totalCount", 0)
                self._log(
                    "info",
                    f"Successfully retrieved {len(results)} computers from inventory "
                    f"(total: {total_count})",
                )
                return inventory_data
            else:
                error_msg = (
                    f"Failed to retrieve computer inventory. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error retrieving computer inventory: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)

    def erase_computer(
        self,
        computer_id: str,
        pin: str = None,
        obliteration_behavior: str = None,
        return_to_service: bool = False,
        mdm_profile_data: str = None,
        wifi_profile_data: str = None,
    ) -> dict:
        """
        Erase/wipe a managed computer remotely using ERASE_DEVICE MDM command

        Args:
            computer_id (str): The ID of the computer to erase
            pin (str, optional): 6-digit PIN for the erase command
            obliteration_behavior (str): Obliteration behavior - "Default",
                "DoNotObliterate", "ObliterateWithWarning", "Always"
            return_to_service (bool): Whether to enable return to service after erase
            mdm_profile_data (str, optional): Base64-encoded MDM profile data for return to service
            wifi_profile_data (str, optional): Base64-encoded WiFi profile data
                for return to service

        Returns:
            dict: API response containing erase command status

        Raises:
            JamfInvalidParameterError: If computer_id is invalid or parameters are wrong
            JamfError: If the API request fails
        """
        try:
            # Validate computer_id
            if not computer_id or not str(computer_id).strip():
                raise JamfInvalidParameterError("Computer ID is required and cannot be empty")

            # Validate PIN if provided
            if pin is not None:
                pin_str = str(pin).strip()
                if pin_str and (not pin_str.isdigit() or len(pin_str) != 6):
                    raise JamfInvalidParameterError("PIN must be a 6-digit number")
                pin = pin_str if pin_str else None

            # Validate return to service requirements
            if return_to_service and not mdm_profile_data and not wifi_profile_data:
                raise JamfInvalidParameterError(
                    "Return to Service is enabled but no profile data provided. "
                    "At least one of MDM Profile Data or WiFi Profile Data is required."
                )

            self._log("info", f"Erasing computer with ID: {computer_id}")

            # Ensure token is valid
            if not self.check_token_expiration():
                raise JamfError("Failed to obtain valid access token")

            # First, get device information to obtain managementId
            device_info = self.get_device_info(computer_id)
            management_id = device_info.get("general", {}).get("managementId")

            if not management_id:
                raise JamfError(f"Could not retrieve management ID for computer {computer_id}")

            self._log("info", f"Retrieved management ID: {management_id}")

            # Prepare command data
            command_data = {
                "commandType": "ERASE_DEVICE",
                "obliterationBehavior": obliteration_behavior,
            }

            # Add PIN if provided
            if pin:
                command_data["pin"] = pin
                self._log("info", "Erase command will use provided PIN")

            # Add return to service settings if enabled
            if return_to_service:
                return_to_service = {"enabled": True}

                if mdm_profile_data:
                    return_to_service["mdmProfileData"] = mdm_profile_data

                if wifi_profile_data:
                    return_to_service["wifiProfileData"] = wifi_profile_data

                command_data["returnToService"] = return_to_service
                self._log("info", "Return to service enabled for erase command")

            # Prepare request body
            request_body = {
                "commandData": command_data,
                "clientData": [{"managementId": management_id}],
            }

            # Make API request
            url = self._get_full_url(API_ENDPOINTS["mdm_commands"])
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            }

            self._log("info", f"Making ERASE_DEVICE MDM command request to: {url}")
            self._log("info", f"Command data: {command_data}")

            response = self.session.post(url, headers=headers, json=request_body, timeout=30)

            if response.status_code == 201:
                result = response.json()
                self._log(
                    "info",
                    f"Successfully initiated ERASE_DEVICE command for computer {computer_id}",
                )
                return result
            elif response.status_code == 404:
                error_msg = f"Computer with ID {computer_id} not found or not managed"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            elif response.status_code == 403:
                error_msg = "Insufficient permissions to erase computer"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            elif response.status_code == 400:
                error_msg = "Invalid request parameters for erase command"
                try:
                    error_data = response.json()
                    if "errors" in error_data:
                        error_msg = "; ".join([
                            err.get("description", str(err)) for err in error_data["errors"]
                        ])
                except Exception:
                    pass
                self._log("error", f"Bad request: {error_msg}")
                raise JamfInvalidParameterError(f"Bad request: {error_msg}")
            else:
                error_msg = f"Status: {response.status_code}, Response: {response.text}"
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except JamfError:
            raise
        except JamfInvalidParameterError:
            raise
        except Exception as e:
            self._log("error", f"Error erasing computer {computer_id}: {e}")
            raise JamfError(f"Failed to erase computer: {e}")

    def remote_lock_device(self, computer_id, pin, message=None, phone_number=None) -> dict:
        """
        Send a remote lock command to a managed device

        Args:
            computer_id (str): The ID of the computer to lock
            pin (str): 6-digit PIN code that will be required to unlock the device
            message (str, optional): Custom message to display on the locked device
            phone_number (str, optional): Phone number to display on the locked device

        Returns:
            dict: API response containing lock command status

        Raises:
            JamfInvalidParameterError: If computer_id is invalid or PIN format is wrong
            JamfError: If the API request fails
        """
        try:
            # Validate computer_id
            if not computer_id or not str(computer_id).strip():
                raise JamfInvalidParameterError("Computer ID is required and cannot be empty")

            # Validate PIN (required and must be 6 digits)
            if not pin or not str(pin).isdigit() or len(str(pin)) != 6:
                raise JamfInvalidParameterError("PIN is required and must be exactly 6 digits")

            self._log("info", f"Sending remote lock command to computer ID: {computer_id}")

            # Ensure token is valid
            self.check_token_expiration()

            # Step 1: Get device information to retrieve managementId
            self._log("info", f"Retrieving device information for computer ID: {computer_id}")
            device_info = self.get_device_info(computer_id)

            # Extract managementId from device info
            management_id = device_info.get("general", {}).get("managementId")
            if not management_id:
                raise JamfError(f"Could not retrieve managementId for computer {computer_id}")

            self._log(
                "info",
                f"Retrieved managementId: {management_id} for computer ID: {computer_id}",
            )

            # Use the admin-provided PIN for the lock command
            device_lock_pin = str(pin)
            self._log(
                "info",
                f"Using admin-provided PIN for remote lock of computer ID: {computer_id}",
            )

            # Prepare request body for device_lock MDM command
            request_body = {
                "clientData": [{"managementId": str(management_id)}],
                "commandData": {"commandType": "DEVICE_LOCK"},
            }

            # Add PIN to commandData (required for unlock)
            request_body["commandData"]["pin"] = device_lock_pin
            self._log("info", "Lock command includes admin-provided PIN for unlocking")

            if message:
                request_body["commandData"]["message"] = str(message).strip()
                self._log("info", "Lock command will include custom message")

            if phone_number:
                request_body["commandData"]["phoneNumber"] = str(phone_number).strip()
                self._log("info", "Lock command will include phone number")

            # Make API request
            url = self._get_full_url(API_ENDPOINTS["mdm_commands"])
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            self._log("info", f"Making remote lock request to: {url}")
            self._log("info", f"Request body: {request_body}")

            response = self.session.post(url, headers=headers, json=request_body, timeout=30)

            if response.status_code == 201:
                try:
                    result = response.json()
                except Exception:
                    # Some endpoints may return empty body on success
                    result = {"status": "success", "message": "Remote lock command initiated"}
                self._log(
                    "info",
                    f"Successfully initiated remote lock command for computer {computer_id}",
                )
                return result
            elif response.status_code == 200:
                try:
                    result = response.json()
                except Exception:
                    result = {"status": "success", "message": "Remote lock command initiated"}
                self._log(
                    "info",
                    f"Successfully initiated remote lock command for computer {computer_id}",
                )
                return result
            elif response.status_code == 404:
                error_msg = f"Computer with ID {computer_id} not found"
                self._log("error", error_msg)
                raise Exception(error_msg)
            elif response.status_code == 403:
                error_msg = "Insufficient permissions to send remote lock command"
                self._log("error", error_msg)
                raise Exception(error_msg)
            elif response.status_code == 400:
                error_msg = "Invalid request parameters"
                try:
                    error_data = response.json()
                    if "errors" in error_data:
                        error_msg = "; ".join([
                            err.get("description", str(err)) for err in error_data["errors"]
                        ])
                except Exception:
                    pass
                self._log("error", f"Bad request: {error_msg}")
                raise Exception(f"Bad request: {error_msg}")
            else:
                self._log("error", f"Unexpected response status: {response.status_code}")
                self._log("error", f"Response content: {response.text}")
                error_msg = f"Failed to send remote lock command. Status: {response.status_code}"
                raise Exception(error_msg)

        except Exception as e:
            self._log("error", f"Error sending remote lock command to computer {computer_id}: {e}")
            raise Exception(f"Failed to send remote lock command: {e}")

    def assign_to_group(
        self, group_id, computer_ids=None, computer_names=None, computer_serial_numbers=None
    ):
        """
        Add computers to a computer group

        Args:
            group_id (str): The ID of the computer group
            computer_ids (list, optional): List of computer IDs to add
            computer_names (list, optional): List of computer names to add
            computer_serial_numbers (list, optional): List of serial numbers to add

        Returns:
            dict: API response containing the updated group information

        Raises:
            JamfError: If the API request fails
        """
        try:
            self._log("info", f"Assigning computers to group {group_id}")

            # Validate input parameters
            if not group_id:
                raise JamfInvalidParameterError("Group ID is required")

            if not computer_ids and not computer_names and not computer_serial_numbers:
                raise JamfInvalidParameterError(
                    "At least one computer identifier (ID, name, or serial number) must be provided"
                )

            # Ensure we have a valid token
            self.check_token_expiration()

            # Build XML request body
            computers_xml = []

            # Process computer IDs
            if computer_ids:
                for comp_id in computer_ids:
                    computers_xml.append(f"<computer><id>{comp_id}</id></computer>")

            # Process computer names
            if computer_names:
                for comp_name in computer_names:
                    computers_xml.append(f"<computer><name>{comp_name}</name></computer>")

            # Process serial numbers
            if computer_serial_numbers:
                for serial in computer_serial_numbers:
                    computers_xml.append(
                        f"<computer><serial_number>{serial}</serial_number></computer>"
                    )

            # Build the appropriate XML structure
            xml_body = f"""<?xml version="1.0" encoding="UTF-8"?>
                            <computer_group>
                                <computer_additions>
                                    {"".join(computers_xml)}
                                </computer_additions>
                            </computer_group>"""

            # Make API request to Classic API endpoint
            url = self._get_full_url(API_ENDPOINTS["update_computer_group"].format(id=group_id))
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/xml",
                "Content-Type": "application/xml",
            }

            self._log("info", f"Making request to: {url}")
            self._log("info", f"Computer count: {len(computers_xml)}")

            response = self.session.put(url, headers=headers, data=xml_body, timeout=30)

            if response.status_code == 201:
                # Parse XML response (Classic API returns XML)
                try:
                    import xml.etree.ElementTree as ET

                    root = ET.fromstring(response.text)

                    # Extract basic group info from XML response
                    result = {
                        "status": "success",
                        "group_id": group_id,
                        "computers_processed": len(computers_xml),
                        "message": (
                            f"Successfully added {len(computers_xml)} computer(s) "
                            f"to group {group_id}"
                        ),
                    }

                    # Try to extract group name if available
                    name_elem = root.find(".//name")
                    if name_elem is not None:
                        result["group_name"] = name_elem.text

                    self._log("info", f"Successfully added computers to group {group_id}")
                    return result
                except Exception as parse_error:
                    self._log("info", f"Could not parse XML response: {parse_error}")
                    # Return basic success response
                    return {
                        "status": "success",
                        "group_id": group_id,
                        "computers_processed": len(computers_xml),
                        "message": (
                            f"Successfully added {len(computers_xml)} computer(s) "
                            f"to group {group_id}"
                        ),
                    }
            elif response.status_code == 400:
                error_msg = "Invalid request parameters or XML format"
                try:
                    # Try to extract error from XML response
                    import xml.etree.ElementTree as ET

                    root = ET.fromstring(response.text)
                    error_elem = root.find(".//error")
                    if error_elem is not None:
                        error_msg = error_elem.text
                except Exception:
                    pass
                self._log("error", f"Bad request: {error_msg}")
                raise JamfInvalidParameterError(f"Bad request: {error_msg}")
            elif response.status_code == 404:
                self._log("error", f"Computer group with ID {group_id} not found")
                raise JamfError(f"Computer group with ID {group_id} not found")
            elif response.status_code == 401:
                self._log("error", "Authentication failed")
                raise JamfError("Authentication failed - check API credentials")
            elif response.status_code == 403:
                self._log("error", "Insufficient permissions")
                raise JamfError("Insufficient permissions to modify computer groups")
            else:
                self._log("error", f"Unexpected response status: {response.status_code}")
                self._log("error", f"Response content: {response.text}")
                raise JamfError(
                    f"Failed to assign computers to group. Status: {response.status_code}"
                )

        except JamfError:
            raise
        except JamfInvalidParameterError:
            raise
        except Exception as e:
            self._log("error", f"Error assigning computers to group: {e}")
            raise JamfError(f"Failed to assign computers to group: {e}")

    def update_computer_extension_attribute(
        self, computer_id: str, extension_attribute: dict
    ) -> dict:
        """
        Update extension attributes for a computer

        Args:
            computer_id (str): The ID of the computer to update extension attributes for
            extension_attribute (dict): Dictionary with 'definitionId' and 'values' keys
                Example: {"definitionId": "1", "values": ["Value1", "Value2"]}

        Returns:
            dict: API response containing the updated computer information

        Raises:
            JamfInvalidParameterError: If computer_id is invalid or
                extension_attribute format is wrong
            JamfError: If the API request fails
        """
        try:
            # Validate computer_id
            if not computer_id or not str(computer_id).strip():
                raise JamfInvalidParameterError("Computer ID is required and cannot be empty")

            # Validate extension_attribute
            if not extension_attribute or not isinstance(extension_attribute, dict):
                raise JamfInvalidParameterError(
                    "Extension attribute must be provided as a dictionary"
                )

            # Validate each extension attribute
            if "definitionId" not in extension_attribute or "values" not in extension_attribute:
                raise JamfInvalidParameterError(
                    "Extension attribute must have 'definitionId' and 'values' keys"
                )
            if not str(extension_attribute["definitionId"]).strip():
                raise JamfInvalidParameterError(
                    "Extension attribute must have a non-empty 'definitionId'"
                )
            if (
                not isinstance(extension_attribute["values"], list)
                or not extension_attribute["values"]
            ):
                raise JamfInvalidParameterError(
                    "Extension attribute must have a non-empty 'values' list"
                )

            # Ensure we have a valid token
            if not self.check_token_expiration():
                raise JamfError("Failed to obtain valid access token")

            # Construct the API URL
            url = self._get_full_url(
                API_ENDPOINTS["computer_inventory_detail"].format(id=computer_id)
            )

            # Prepare request body with extension attributes
            request_body = {"extensionAttributes": []}

            # For the single extension attribute, create entries for each value
            for value in extension_attribute["values"]:
                request_body["extensionAttributes"].append({
                    "definitionId": str(extension_attribute["definitionId"]),
                    "values": [str(value)],
                })

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            self._log("info", f"Updating extension attributes for computer ID: {computer_id}")
            self._log("info", f"Making request to: {url}")
            self._log(
                "info",
                f"Updating extension attribute with {len(extension_attribute['values'])} value(s)",
            )

            response = self.session.patch(url, headers=headers, json=request_body, timeout=30)

            if response.status_code == 200:
                result = response.json()
                self._log(
                    "info", f"Successfully updated extension attributes for computer {computer_id}"
                )
                return result
            elif response.status_code == 404:
                error_msg = f"Computer with ID {computer_id} not found"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            elif response.status_code == 400:
                error_msg = "Bad request - invalid extension attribute data or format"
                self._log("error", error_msg)
                self._log("error", f"Response: {response.text}")
                raise JamfInvalidParameterError(error_msg)
            elif response.status_code == 401:
                error_msg = "Authentication failed - check API credentials"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            elif response.status_code == 403:
                error_msg = "Insufficient permissions to update computer extension attributes"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            else:
                error_msg = (
                    f"Failed to update extension attributes. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except JamfError:
            raise
        except JamfInvalidParameterError:
            raise
        except Exception as e:
            self._log("error", f"Error updating extension attributes: {e}")
            raise JamfError(f"Failed to update extension attributes: {e}")

    def list_computer_extension_attributes(self) -> list:
        """
        List all computer extension attributes from Jamf Pro

        Returns:
            list: List of extension attribute dictionaries with id, name, and description

        Raises:
            JamfError: If the API request fails
        """
        try:
            # Ensure we have a valid token
            if not self.check_token_expiration():
                raise JamfError("Failed to obtain valid access token")

            # Construct the API URL
            url = self._get_full_url(API_ENDPOINTS["computer_extension_attributes"])

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            }

            self._log("info", f"Retrieving computer extension attributes from: {url}")

            response = self.session.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                extension_attributes = result.get("computer_extension_attributes", [])

                # Format the attributes for dropdown usage
                formatted_attributes = []
                for attr in extension_attributes:
                    formatted_attributes.append({
                        "id": str(attr.get("id", "")),
                        "name": attr.get("name", "Unknown"),
                        "description": attr.get("description", ""),
                        "display_name": (
                            f"{attr.get('name', 'Unknown')} (ID: {attr.get('id', 'N/A')})"
                        ),
                    })

                self._log(
                    "info",
                    f"Successfully retrieved {len(formatted_attributes)} extension attributes",
                )
                return formatted_attributes
            elif response.status_code == 404:
                error_msg = "Computer extension attributes endpoint not found"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            elif response.status_code == 401:
                error_msg = "Authentication failed - check API credentials"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            elif response.status_code == 403:
                error_msg = "Insufficient permissions to view computer extension attributes"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            else:
                error_msg = (
                    f"Failed to retrieve extension attributes. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except JamfError:
            raise
        except Exception as e:
            self._log("error", f"Error retrieving extension attributes: {e}")
            raise JamfError(f"Failed to retrieve extension attributes: {e}")

    def _clean_string_for_json(self, obj):
        """
        Recursively clean string values in data structures to prevent JSON parsing issues.

        This method handles complex JSON cleaning including:
        - Extension attributes with unescaped quotes and special characters
        - Certificate data with embedded quotes and newlines
        - Group membership data with structural issues
        - Trailing commas and malformed JSON structures

        Args:
            obj: The object to clean (dict, list, str, or other)

        Returns:
            Cleaned object with properly escaped string values
        """
        if isinstance(obj, dict):
            return {key: self._clean_string_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_string_for_json(item) for item in obj]
        elif isinstance(obj, str):
            return self._clean_json_string(obj)
        else:
            # Return non-string values as-is
            return obj

    def _clean_json_string(self, json_string: str) -> str:
        """
        Clean a JSON string by fixing common issues that cause parsing errors.

        This is a direct port of the cleanJsonData function from GetDeviceInformation.html widget.

        Handles:
        - Unescaped quotes within string values
        - Newlines, tabs, and control characters
        - Trailing commas before } or ]
        - Certificate data with embedded quotes
        - Extension attributes with special characters
        - Filter criteria with embedded quotes
        - Group descriptions with complex formatting

        Args:
            json_string: The JSON string to clean

        Returns:
            Cleaned JSON string
        """
        if not isinstance(json_string, str):
            return json_string

        result = ""
        escape_next = False
        in_string = True

        def find_next_non_whitespace(start_index: int) -> str:
            """Find next non-whitespace character from given index."""
            for k in range(start_index, len(json_string)):
                if json_string[k] not in " \t\n\r":
                    return json_string[k]
            return None

        for i, char in enumerate(json_string):
            if escape_next:
                # If we're escaping the next character, just add it as-is
                result += char
                escape_next = False
                continue

            if char == "\\":
                # Check specifically for \, sequences
                if i + 1 < len(json_string) and json_string[i + 1] == ",":
                    # Convert \, to \\, for valid JSON
                    result += "\\\\"
                    i += 1  # Skip the comma since we've processed it
                    continue

                # Mark that we should escape the next character
                result += char
                escape_next = True
                continue

            if char == '"':
                # For unescaped quotes, determine if this ends/starts a string or is content within
                if in_string:
                    # We're currently in a string - check if this quote actually ends it
                    next_non_whitespace = find_next_non_whitespace(i + 1)

                    # If followed by valid JSON terminators, this ends the string
                    if next_non_whitespace in [",", "}", "]", ":", None]:
                        in_string = False
                        result += char
                    else:
                        # This quote is content within the string - escape it
                        result += '\\"'
                else:
                    # We're not in a string - this quote starts a new string
                    in_string = True
                    result += char
                continue

            if in_string:
                # Inside a string value - escape special characters
                if char == "\n":
                    result += "\\n"
                elif char == "\r":
                    result += "\\r"
                elif char == "\t":
                    result += "\\t"
                elif char == "\b":
                    result += "\\b"
                elif char == "\f":
                    result += "\\f"
                else:
                    result += char
            else:
                # Outside string values - handle structural issues
                if char == ",":
                    # Skip trailing commas before } or ]
                    next_non_whitespace = find_next_non_whitespace(i + 1)
                    if next_non_whitespace in ["}", "]"]:
                        continue
                result += char

        return result

    def get_mobile_device_detail(self, device_id: str) -> dict:
        """
        Get detailed mobile device information from Jamf Pro using v2 API.

        Args:
            device_id (str): The ID of the mobile device to retrieve information for

        Returns:
            dict: Mobile device information including management ID

        Raises:
            JamfInvalidParameterError: If device_id is invalid
            JamfError: If the API request fails
        """
        try:
            # Validate device_id
            if not device_id or not str(device_id).strip():
                raise JamfInvalidParameterError("Device ID is required and cannot be empty")

            # Ensure we have a valid token
            if not self.check_token_expiration():
                raise JamfError("Failed to obtain valid access token")

            # Construct the API URL
            url = self._get_full_url(
                API_ENDPOINTS["mobile_device_inventory_detail"].format(id=device_id)
            )

            self._log("info", f"Retrieving mobile device details for ID: {device_id}")

            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                device_data = response.json()
                self._log(
                    "info",
                    f"Successfully retrieved mobile device details for ID: {device_id}",
                )
                return device_data
            elif response.status_code == 404:
                error_msg = f"Mobile device with ID {device_id} not found"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            else:
                error_msg = (
                    f"Failed to retrieve mobile device details. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except JamfError:
            raise
        except JamfInvalidParameterError:
            raise
        except Exception as e:
            self._log("error", f"Error retrieving mobile device details: {e}")
            raise JamfError(f"Failed to retrieve mobile device details: {e}")

    def remote_lock_mobile_device(
        self, device_id: str, message: str = None, phone_number: str = None
    ) -> dict:
        """
        Send a remote lock command to a managed mobile device.

        Args:
            device_id (str): The ID of the mobile device to lock
            message (str, optional): Custom message to display on the locked device
            phone_number (str, optional): Phone number to display on the locked device

        Returns:
            dict: API response containing lock command status

        Raises:
            JamfInvalidParameterError: If device_id is invalid
            JamfError: If the API request fails
        """
        try:
            # Validate device_id
            if not device_id or not str(device_id).strip():
                raise JamfInvalidParameterError("Device ID is required and cannot be empty")

            # Ensure we have a valid token
            if not self.check_token_expiration():
                raise JamfError("Failed to obtain valid access token")

            # First, get the mobile device details to obtain the management ID
            self._log("info", f"Retrieving mobile device details for ID: {device_id}")
            device_details = self.get_mobile_device_detail(device_id)

            # Extract management ID from device details
            management_id = None

            if "managementId" in device_details:
                management_id = device_details.get("managementId")

            if not management_id:
                raise JamfError(f"Could not find management ID for mobile device {device_id}. ")

            self._log("info", f"Retrieved management ID: {management_id}")

            # Prepare request body for device_lock MDM command
            request_body = {
                "clientData": [{"managementId": str(management_id)}],
                "commandData": {"commandType": "DEVICE_LOCK"},
            }

            if message:
                request_body["commandData"]["message"] = str(message).strip()
                self._log("info", "Lock command will include custom message")

            if phone_number:
                request_body["commandData"]["phoneNumber"] = str(phone_number).strip()
                self._log("info", "Lock command will include phone number")

            # Make API request
            url = self._get_full_url(API_ENDPOINTS["mdm_commands"])
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            self._log("info", f"Making remote lock request to: {url}")
            self._log("info", f"Request body: {request_body}")

            response = self.session.post(url, headers=headers, json=request_body, timeout=30)

            if response.status_code == 201:
                try:
                    result = response.json()
                except Exception:
                    # Some endpoints may return empty body on success
                    result = {"status": "success", "message": "Remote lock command initiated"}
                self._log(
                    "info",
                    f"Successfully initiated remote lock command for mobile device {device_id}",
                )
                return result
            elif response.status_code == 200:
                try:
                    result = response.json()
                except Exception:
                    result = {"status": "success", "message": "Remote lock command initiated"}
                self._log(
                    "info",
                    f"Successfully initiated remote lock command for mobile device {device_id}",
                )
                return result
            elif response.status_code == 404:
                error_msg = f"Mobile device with ID {device_id} not found"
                self._log("error", error_msg)
                raise Exception(error_msg)
            elif response.status_code == 403:
                error_msg = "Insufficient permissions to send remote lock command"
                self._log("error", error_msg)
                raise Exception(error_msg)
            elif response.status_code == 400:
                error_msg = "Invalid request parameters"
                try:
                    error_data = response.json()
                    if "errors" in error_data:
                        error_msg = "; ".join([
                            err.get("description", str(err)) for err in error_data["errors"]
                        ])
                except Exception:
                    pass
                self._log("error", f"Bad request: {error_msg}")
                raise Exception(f"Bad request: {error_msg}")
            else:
                self._log("error", f"Unexpected response status: {response.status_code}")
                self._log("error", f"Response content: {response.text}")
                error_msg = f"Status: {response.status_code}"
                raise Exception(error_msg)
        except Exception as e:
            self._log("error", f"Error sending remote lock command to mobile device: {e}")
            raise JamfError(f"Failed to send remote lock command to mobile device: {e}")

    def erase_mobile_device(
        self,
        device_id: str,
        preserve_data_plan: bool = False,
        disallow_proximity_setup: bool = False,
        return_to_service: bool = False,
        mdm_profile_data: str = None,
        wifi_profile_data: str = None,
        bootstrap_token: str = None,
    ) -> dict:
        """
        Erase/wipe a mobile device remotely using ERASE_DEVICE MDM command

        Args:
            device_id (str): The ID of the mobile device to erase
            preserve_data_plan (bool): Whether to preserve the data plan during erase
            disallow_proximity_setup (bool): Whether to disallow proximity setup during erase
            return_to_service (bool): Whether to enable return to service after erase
            mdm_profile_data (str, optional): Base64-encoded MDM profile data for return to service
            wifi_profile_data (str, optional): Base64-encoded WiFi profile data
                for return to service
            bootstrap_token (str, optional): Bootstrap token for return to service

        Returns:
            dict: API response containing erase command status

        Raises:
            JamfInvalidParameterError: If device_id is invalid or parameters are wrong
            JamfError: If the API request fails
        """
        try:
            # Validate device_id
            if not device_id or not str(device_id).strip():
                raise JamfInvalidParameterError("Device ID is required and cannot be empty")

            self._log("info", f"Erasing mobile device with ID: {device_id}")

            # Ensure token is valid
            if not self.check_token_expiration():
                raise JamfError("Failed to obtain valid access token")

            # First, get device information to obtain managementId
            device_info = self.get_mobile_device_detail(device_id)
            management_id = device_info.get("managementId")

            if not management_id:
                raise JamfError(f"Could not retrieve management ID for mobile device {device_id}")

            self._log("info", f"Retrieved management ID: {management_id}")

            # Prepare command data
            command_data = {
                "commandType": "ERASE_DEVICE",
            }

            # Add preserve data plan if provided
            if preserve_data_plan:
                command_data["preserveDataPlan"] = preserve_data_plan
                self._log("info", "Erase command will preserve data plan")

            # Add disallow proximity setup if provided
            if disallow_proximity_setup:
                command_data["disallowProximitySetup"] = disallow_proximity_setup
                self._log("info", "Erase command will disallow proximity setup")

            # Add return to service settings if enabled
            if return_to_service:
                return_to_service = {"enabled": True}

                if mdm_profile_data:
                    return_to_service["mdmProfileData"] = mdm_profile_data

                if wifi_profile_data:
                    return_to_service["wifiProfileData"] = wifi_profile_data

                if bootstrap_token:
                    return_to_service["bootstrapToken"] = bootstrap_token

                command_data["returnToService"] = return_to_service
                self._log("info", "Return to service enabled for erase command")

            # Prepare request body
            request_body = {
                "commandData": command_data,
                "clientData": [{"managementId": management_id}],
            }

            # Make API request
            url = self._get_full_url(API_ENDPOINTS["mdm_commands"])
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            }

            self._log("info", f"Making ERASE_DEVICE MDM command request to: {url}")
            self._log("info", f"Command data: {command_data}")

            response = self.session.post(url, headers=headers, json=request_body, timeout=30)

            if response.status_code == 201:
                result = response.json()
                self._log(
                    "info",
                    f"Successfully initiated ERASE_DEVICE command for mobile device {device_id}",
                )
                return result
            elif response.status_code == 404:
                error_msg = f"Mobile device with ID {device_id} not found or not managed"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            elif response.status_code == 403:
                error_msg = "Insufficient permissions to erase computer"
                self._log("error", error_msg)
                raise JamfError(error_msg)
            elif response.status_code == 400:
                error_msg = "Invalid request parameters for erase command"
                try:
                    error_data = response.json()
                    if "errors" in error_data:
                        error_msg = "; ".join([
                            err.get("description", str(err)) for err in error_data["errors"]
                        ])
                except Exception:
                    pass
                self._log("error", f"Bad request: {error_msg}")
                raise JamfInvalidParameterError(f"Bad request: {error_msg}")
            else:
                error_msg = (
                    f"Failed to erase mobile device. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except JamfError:
            raise
        except JamfInvalidParameterError:
            raise
        except Exception as e:
            self._log("error", f"Error erasing mobile device {device_id}: {e}")
            raise JamfError(f"Failed to erase mobile device: {e}")

    def get_mobile_device_inventory(
        self, page=0, page_size=100, sort=None, filter_query=None, section=None
    ):
        """
        Retrieve paginated Mobile Device Inventory records from Jamf Pro using v2 API.

        Args:
            page (int): Page number to retrieve (default: 0)
            page_size (int): Number of records per page (default: 100, max: 2000)
            sort (str): Sort criteria (comma-separated list of field:direction pairs)
            filter_query (str): Filter criteria using Jamf Pro API filter syntax
            section (str): Comma-separated list of sections to include in response

        Returns:
            dict: Mobile device inventory data with results and pagination info

        Raises:
            JamfError: If the API request fails
        """
        try:
            # Ensure we have a valid token
            if not self.check_token_expiration():
                raise JamfError("Failed to obtain valid access token")

            # Construct the API URL
            url = self._get_full_url(API_ENDPOINTS["mobile_device_inventory"])

            # Build query parameters
            params = {
                "page": page,
                "page-size": page_size,
            }

            if sort:
                params["sort"] = sort
            if filter_query:
                params["filter"] = filter_query
            if section:
                params["section"] = section

            self._log("info", f"Retrieving mobile device inventory from: {url}")
            self._log("info", f"Parameters: {params}")

            response = self.session.get(url, params=params, timeout=60)

            if response.status_code == 200:
                inventory_data = response.json()

                # Clean the data to prevent JSON parsing issues in widgets
                inventory_data = self._clean_string_for_json(inventory_data)

                total_count = inventory_data.get("totalCount", 0)
                returned_count = len(inventory_data.get("results", []))

                self._log(
                    "info",
                    f"Successfully retrieved {returned_count} mobile devices from page {page} "
                    f"(total: {total_count})",
                )
                return inventory_data
            else:
                error_msg = (
                    f"Failed to retrieve mobile device inventory. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self._log("error", error_msg)
                raise JamfError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error retrieving mobile device inventory: {str(e)}"
            self._log("error", error_msg)
            raise JamfError(error_msg)
