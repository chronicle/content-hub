from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from .constants import OAUTH_CONFIG, ENDPOINT_ENRICH_IP, ENDPOINT_ENRICH_STORAGE, ENDPOINT_JOB_STATUS, ENDPOINT_TAKE_SNAPSHOT, ENDPOINT_VOLUME_OFFLINE, RRS_SERVICE_URL, SSL_VERIFY
from .auth_manager import RRSOAuthAdapter, RRSOAuthManager
from .utils import generate_encryption_key, extract_domain_from_uri, build_rrs_url
from TIPCommon.oauth import CredStorage
import requests


class ApiManager:
   def __init__(self, siemplify: SiemplifyAction):
        """Initialize the APIManager with OAuth token management.

        OAuth Token Flow:
        1. Fetch access_token from encrypted storage
        2. If found and valid, use it for API calls
        3. If not found or expired, generate new access_token and save

        Args:
            siemplify: Chronicle SOAR SDK instance for logging and context storage
        """
        self.siemplify = siemplify
        self.session = requests.Session()
        
        # Get credentials from Integration config
        self.CLIENT_ID = self.siemplify.extract_configuration_param('Integration', "client id")
        self.CLIENT_SECRET = self.siemplify.extract_configuration_param('Integration', "client secret")
        self.ACCOUNT_ID = self.siemplify.extract_configuration_param('Integration', "account id")

        self.ENDPOINT_URL = RRS_SERVICE_URL
        self.SSL_VERIFY = SSL_VERIFY
        
        self.DOMAIN = extract_domain_from_uri(self.ENDPOINT_URL)

        self.siemplify.LOGGER.info(f"ApiManager: SAAS Domain={self.DOMAIN}, Verify SSL={self.SSL_VERIFY}, Account ID={self.ACCOUNT_ID}")
    
        self.token = ""
        
        # Setup OAuth components
        self.oauth_adapter = RRSOAuthAdapter(
            client_id=self.CLIENT_ID,
            client_secret=self.CLIENT_SECRET,
            verify_ssl=self.SSL_VERIFY,
        )
        
        self.cred_storage = CredStorage(
            encryption_password=generate_encryption_key(self.CLIENT_ID, self.DOMAIN),
            chronicle_soar=self.siemplify,
        )
        
        self.oauth_manager = RRSOAuthManager(
            oauth_adapter=self.oauth_adapter,
            cred_storage=self.cred_storage,
        )
        
        # Check if token is expired and get/generate token
        self.is_token_expired = self.oauth_manager._token_is_expired()
        if self.is_token_expired:
            self.siemplify.LOGGER.info("ApiManager: Access token is expired or not found")
        
        self.token = (
            self.oauth_manager._token.access_token
            if self.oauth_manager._token and hasattr(self.oauth_manager._token, "access_token")
            else ""
        )
        
        if not self.token or self.is_token_expired:
            self.siemplify.LOGGER.info(f"ApiManager: generate new token...")
            self.generate_token()
        else:
            self.siemplify.LOGGER.info(f"ApiManager: Valid access token found in CredStorage.")
        
        # Setting HTTP session headers
        self.siemplify.LOGGER.info(f"ApiManager: Setting HTTP session headers")
        self.session.headers.update({"Content-Type": "application/json"})
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})



   def generate_token(self) -> str:
        """Generate and save a new access token.

        This method refreshes the access token using the credentials,
        saves it to encrypted storage, and updates the session headers.
        """
        self.siemplify.LOGGER.info("Generating new token")
        
        token = self.oauth_adapter.refresh_token()
        self.oauth_manager._token = token  # Update manager's token reference
        self.oauth_manager.save_token()
        self.token = token.access_token
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        self.siemplify.LOGGER.info("ApiManager.generate_token - Token generated and saved successfully")
        
        return self.token

   def is_token_valid(self):
        """Returns boolean indicating token expiry status"""
        return not self.oauth_manager._token_is_expired()


   def enrich_ip(self, ip_address: str) -> list[dict]:
        """
        Call the IP enrichment API to get enrichment data for an IP address.

        Args:
            ip_address: IP address to enrich

        Returns:
            Response data from the enrichment API

        Example:
            >>> manager = ApiManager(siemplify)
            >>> manager.auth()
            >>> response = manager.enrich_ip("192.168.1.1")
            >>> print(response)
        """
        self.siemplify.LOGGER.info(f"ApiManager.enrich_ip: Enriching IP address: {ip_address}")

        # Build full URL
        url = build_rrs_url(self.ENDPOINT_URL, self.ACCOUNT_ID, ENDPOINT_ENRICH_IP)
        # url = f"{self.ENDPOINT_URL}/{self.ACCOUNT_ID}/{ENDPOINT_ENRICH_IP}"

        request_payload = {
            "ip_address": ip_address
        }

        self.siemplify.LOGGER.info(f"ApiManager.enrich_ip: POST URL={url}")

        # Make API call using session (already has Authorization header from auth())
        response = self.session.post(url, json=request_payload, verify=self.SSL_VERIFY)

        # Check if request was successful
        response.raise_for_status()

        # Parse response
        response_data = response.json()
        self.siemplify.LOGGER.info(f"ApiManager.enrich_ip: API call successful. Status: {response.status_code}")
        self.siemplify.LOGGER.info(f"ApiManager.enrich_ip: Response data: {response_data}")

        return response_data



   def enrich_storage(self) -> list[dict]:
        """
        Enrich storage information.

        Extracts storage parameters from action and retrieves enrichment data.

        Returns:
            Response data from the storage enrichment API

        Example:
            >>> manager = ApiManager(siemplify)
            >>> response = manager.enrich_storage()
            >>> print(response)
        """
        # Extract parameters from action
        agent_id = self.siemplify.extract_action_param("agent_id", print_value=True)
        system_id = self.siemplify.extract_action_param("system_id", print_value=True)
        
        self.siemplify.LOGGER.info(f"ApiManager.enrich_storage: Enriching storage for agent_id: {agent_id}, system_id: {system_id}")

        # Build full URL
        url = build_rrs_url(self.ENDPOINT_URL, self.ACCOUNT_ID, ENDPOINT_ENRICH_STORAGE)

        # Build query parameters
        params = {
            "agent_id": agent_id,
            "system_id": system_id
        }

        self.siemplify.LOGGER.info(f"ApiManager.enrich_storage: GET URL={url}, {params=}")

        # Make API call using session (already has Authorization header from __init__)
        response = self.session.get(url, params=params, verify=self.SSL_VERIFY)

        # Check if request was successful
        response.raise_for_status()

        # Parse response
        response_data = response.json()
        self.siemplify.LOGGER.info(f"ApiManager.enrich_storage: API call successful. Status: {response.status_code}")
        self.siemplify.LOGGER.info(f"ApiManager.enrich_storage: Response data: {response_data}")

        return response_data


   def check_job_status(self) -> dict:
        """
        Check the status of a job.

        Extracts job parameters from action and checks job status.

        Returns:
            Response data from the job status API

        Example:
            >>> manager = ApiManager(siemplify)
            >>> response = manager.check_job_status()
            >>> print(response)
        """
        # Extract parameters from action
        source = self.siemplify.extract_action_param("source", print_value=True)
        agent_id = self.siemplify.extract_action_param("agent_id", print_value=True)
        job_id = self.siemplify.extract_action_param("job_id", print_value=True)
        
        self.siemplify.LOGGER.info(f"ApiManager.check_job_status: Checking job status for job_id: {job_id}, source: {source}, agent_id: {agent_id}")

        # Build full URL
        url = build_rrs_url(self.ENDPOINT_URL, self.ACCOUNT_ID, ENDPOINT_JOB_STATUS)

        # Build query parameters
        params = {
            "source": source,
            "agent_id": agent_id,
            "job_id": job_id
        }

        self.siemplify.LOGGER.info(f"ApiManager.check_job_status: GET URL={url}, {params=}")

        # Make API call using session (already has Authorization header from __init__)
        response = self.session.get(url, params=params, verify=self.SSL_VERIFY)

        # Check if request was successful
        response.raise_for_status()

        # Parse response
        response_data = response.json()
        self.siemplify.LOGGER.info(f"ApiManager.check_job_status: API call successful. Status: {response.status_code}")
        self.siemplify.LOGGER.info(f"ApiManager.check_job_status: Response data: {response_data}")

        return response_data


   def take_snapshot(self) -> dict:
        """
        Take a snapshot of a volume.

        Extracts snapshot parameters from action and triggers snapshot creation.

        Returns:
            Response data from the snapshot API

        Example:
            >>> manager = ApiManager(siemplify)
            >>> response = manager.take_snapshot()
            >>> print(response)
        """
        # Extract parameters from action
        volume_id = self.siemplify.extract_action_param("volume_id", print_value=True)
        agent_id = self.siemplify.extract_action_param("agent_id", print_value=True)
        system_id = self.siemplify.extract_action_param("system_id", print_value=True)
        
        # Validate required parameters
        if not volume_id:
            raise ValueError("take_snapshot: volume_id parameter is required")
        if not agent_id:
            raise ValueError("take_snapshot: agent_id parameter is required")
        if not system_id:
            raise ValueError("take_snapshot: system_id parameter is required")

        self.siemplify.LOGGER.info(f"ApiManager.take_snapshot: Taking snapshot for volume_id: {volume_id}, agent_id: {agent_id}, system_id: {system_id}")

        # Build full URL
        url = build_rrs_url(self.ENDPOINT_URL, self.ACCOUNT_ID, ENDPOINT_TAKE_SNAPSHOT)

        # Build request payload
        request_payload = {
            "volume_id": volume_id,
            "agent_id": agent_id,
            "system_id": system_id
        }

        self.siemplify.LOGGER.info(f"ApiManager.take_snapshot: POST URL={url}")

        # Make API call using session (already has Authorization header from __init__)
        response = self.session.post(url, json=request_payload, verify=self.SSL_VERIFY)

        # Check if request was successful
        response.raise_for_status()

        # Parse response
        response_data = response.json()
        self.siemplify.LOGGER.info(f"ApiManager.take_snapshot: API call successful. Status: {response.status_code}")
        self.siemplify.LOGGER.info(f"ApiManager.take_snapshot: Response data: {response_data}")

        return response_data


   def volume_offline(self) -> dict:
        """
        Take a volume offline.

        Extracts volume parameters from action and takes the volume offline.

        Returns:
            Response data from the volume offline API

        Example:
            >>> manager = ApiManager(siemplify)
            >>> response = manager.volume_offline()
            >>> print(response)
        """
        # Extract parameters from action
        volume_id = self.siemplify.extract_action_param("volume_id", print_value=True)
        agent_id = self.siemplify.extract_action_param("agent_id", print_value=True)
        system_id = self.siemplify.extract_action_param("system_id", print_value=True)
        
        # Validate required parameters
        if not volume_id:
            raise ValueError("volume_offline: volume_id parameter is required")
        if not agent_id:
            raise ValueError("volume_offline: agent_id parameter is required")
        if not system_id:
            raise ValueError("volume_offline: system_id parameter is required")

        self.siemplify.LOGGER.info(f"ApiManager.volume_offline: Taking volume offline for volume_id: {volume_id}, agent_id: {agent_id}, system_id: {system_id}")

        # Build full URL
        url = build_rrs_url(self.ENDPOINT_URL, self.ACCOUNT_ID, ENDPOINT_VOLUME_OFFLINE)

        # Build request payload
        request_payload = {
            "volume_id": volume_id,
            "agent_id": agent_id,
            "system_id": system_id
        }

        self.siemplify.LOGGER.info(f"ApiManager.volume_offline: POST URL={url}")

        # Make API call using session (already has Authorization header from __init__)
        response = self.session.post(url, json=request_payload, verify=self.SSL_VERIFY)

        # Check if request was successful
        response.raise_for_status()

        # Parse response
        response_data = response.json()
        self.siemplify.LOGGER.info(f"ApiManager.volume_offline: API call successful. Status: {response.status_code}")
        self.siemplify.LOGGER.info(f"ApiManager.volume_offline: Response data: {response_data}")

        return response_data