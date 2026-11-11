from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING

from TIPCommon.base.interfaces import Apiable
from proofpoint_threat_protection.core.data_parser import ProofpointTPParser

from proofpoint_threat_protection.core.api_utils import get_full_url, validate_response
from requests import Response

from proofpoint_threat_protection.core.auth import AuthenticatedSession

if TYPE_CHECKING:
    from proofpoint_threat_protection.core.data_models import AllowEntry, BlockEntry
    from TIPCommon.base.interfaces.logger import ScriptLogger
    from TIPCommon.types import SingleJson


class ApiParameters(NamedTuple):
    api_root: str
    cluster_id: str


class ProofpointThreatProtectionApiClient(Apiable):
    def __init__(
        self,
        authenticated_session: AuthenticatedSession,
        configuration: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,
            configuration=configuration,
        )
        self.logger: ScriptLogger = logger
        self.api_root: str = configuration.api_root
        self.cluster_id: str = configuration.cluster_id
        self.parser = ProofpointTPParser()

    def test_connectivity(self) -> None:
        """Test connectivity to API."""
        url: str = get_full_url(
            api_root=self.api_root, endpoint_id="get_allow_list_entries"
        )
        params: SingleJson = {"clusterId": self.cluster_id}
        response: Response = self.session.get(url, params=params)
        validate_response(response)

    def get_allow_list_entries(self, cluster_id: str) -> list[AllowEntry]:
        """
        Get entries from the allow list for a given cluster.

        Args:
            cluster_id (str): The cluster ID of the allow list.

        Returns:
            list[AllowEntry]: A list of allow list entries.
        """
        url: str = get_full_url(
            api_root=self.api_root, endpoint_id="get_allow_list_entries"
        )
        params: SingleJson = {"clusterId": cluster_id}
        response: Response = self.session.get(url, params=params)
        validate_response(response)

        return self.parser.parse_allow_list_entries(response.json())

    def add_allow_list_entry(self, cluster_id: str, payload: SingleJson) -> None:
        """
        Add an entry to the allow list for a given cluster.

        Args:
            cluster_id (str): The cluster ID of the allow list.
            payload (SingleJson): The entry to add.
        """
        url: str = get_full_url(
            api_root=self.api_root, endpoint_id="add_allow_list_entry"
        )
        params: SingleJson = {"clusterId": cluster_id}
        response: Response = self.session.post(url, params=params, json=payload)
        validate_response(response)

    def add_block_list_entry(self, cluster_id: str, payload: SingleJson) -> None:
        """
        Add an entry to the block list for a given cluster.

        Args:
            cluster_id (str): The cluster ID of the block list.
            payload (SingleJson): The entry to add.
        """
        url: str = get_full_url(
            api_root=self.api_root, endpoint_id="add_block_list_entry"
        )
        params: SingleJson = {"clusterId": cluster_id}
        response: Response = self.session.post(url, params=params, json=payload)
        validate_response(response)

    def get_block_list_entries(self, cluster_id: str) -> list[BlockEntry]:
        """
        Get entries from the block list for a given cluster.

        Args:
            cluster_id (str): The cluster ID of the block list.

        Returns:
            list[BlockEntry]: A list of block list entries.
        """
        url: str = get_full_url(
            api_root=self.api_root, endpoint_id="get_block_list_entries"
        )
        params: SingleJson = {"clusterId": cluster_id}
        response: Response = self.session.get(url, params=params)
        validate_response(response)

        return self.parser.parse_block_list_entries(response.json())

    def remove_allow_list_entry(self, cluster_id: str, payload: SingleJson) -> None:
        """
        Remove an entry to the Allow list for a given cluster.

        Args:
            cluster_id (str): The cluster ID of the Allow list.
            payload (SingleJson): The entry to remove.
        """
        url: str = get_full_url(
            api_root=self.api_root, endpoint_id="remove_allow_list_entry"
        )
        params: SingleJson = {"clusterId": cluster_id}
        response: Response = self.session.post(url, params=params, json=payload)
        validate_response(response)

    def remove_block_list_entry(self, cluster_id: str, payload: SingleJson) -> None:
        """
        Remove an entry to the Allow list for a given cluster.

        Args:
            cluster_id (str): The cluster ID of the Allow list.
            payload (SingleJson): The entry to remove.
        """
        url: str = get_full_url(
            api_root=self.api_root, endpoint_id="remove_block_list_entry"
        )
        params: SingleJson = {"clusterId": cluster_id}
        response: Response = self.session.post(url, params=params, json=payload)
        validate_response(response)
