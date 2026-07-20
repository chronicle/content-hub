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
import pathlib

import copy
import pytest
from TIPCommon.types import SingleJson
from ..core.constants import MAX_LIMIT
from ..core.datamodels import (
    Incident,
    XQLSearch,
    XQLSearchResult,
    FileRetrievalDetails,
)
from ..core.XDRManager import (
    SearchXQLParameters,
    XDRManager,
)
from ..tests import common
from ..tests.core.product import PaloAltoCortexXDR
from ..tests.core.session import PaloAltoCortexXDRSession


INCIDENT: Incident = common.INCIDENT


class TestApiManager:
    """Unit tests for Integration's XDRManager methods."""

    def test_get_incident_success(
        self,
        manager: XDRManager,
        palo_alto_cortex_xdr: PaloAltoCortexXDR,
        script_session: PaloAltoCortexXDRSession,
    ) -> None:
        """Test get incident success.

        Verify that the get_incident_details method returns the correct incident
        when a valid incident ID is provided.

        Args:
            manager (XDRManager): XDRManager object.
            palo_alto_cortex_xdr (PaloAltoCortexXDR): PaloAltoCortexXDR product object.
            script_session (PaloAltoCortexXDRSession): PaloAltoCortexXDRSession object.
        """
        incident: Incident = copy.deepcopy(INCIDENT)
        palo_alto_cortex_xdr.cleanup_incidents()
        palo_alto_cortex_xdr.add_incident(incident)

        incident = manager.get_incident_details(incident.incident_id, limit=MAX_LIMIT)

        assert incident.incident_id == INCIDENT.incident_id
        assert len(script_session.request_history) == 2

    def test_get_incident_failure(
        self,
        manager: XDRManager,
        script_session: PaloAltoCortexXDRSession,
    ) -> None:
        """Test get incident failure.

        Verify that the get_incident_details method raises an XDRException
        when an invalid incident ID is provided.
        Args:
            manager (XDRManager): XDRManager object.
            zerofox (PaloAltoCortexXDR): PaloAltoCortexXDR product object.
            script_session (PaloAltoCortexXDRSession): PaloAltoCortexXDRSession object.
        """
        with pytest.raises(Exception) as e:
            manager.get_incident_details(
                common.INVALID_INCIDENT_ID,
                limit=MAX_LIMIT,
            )

        assert len(script_session.request_history) == 2
        assert type(e.value).__name__ == "XDRException"
        assert "Incident not found" in str(e.value)

    def test_execute_xql_search_success(
        self,
        manager: XDRManager,
        script_session: PaloAltoCortexXDRSession,
    ) -> None:
        """Test execute xql search success.

        Verify that the execute_xql_search method returns the correct results
        when a valid xql query is provided.

        Args:
            manager (XDRManager): XDRManager object.
            script_session (PaloAltoCortexXDRSession): PaloAltoCortexXDRSession object.
        """
        xql_query: str = "dataset=xdr_data | limit 1"
        search_params: SearchXQLParameters = SearchXQLParameters(
            query=xql_query,
            start_time=0,
            end_time=0,
            limit=1,
        )
        response: SingleJson = manager.execute_xql_search(search_params)

        assert type(response).__name__ == XQLSearch.__name__
        assert len(script_session.request_history) == 2

    def test_get_xql_search_results_success(
        self,
        manager: XDRManager,
        script_session: PaloAltoCortexXDRSession,
    ) -> None:
        """Test get xql search results success.

        Verify that the get_xql_search_results method returns the correct results
        when a valid query ID is provided.

        Args:
            manager (XDRManager): XDRManager object.
            script_session (PaloAltoCortexXDRSession): PaloAltoCortexXDRSession object.
        """
        query_id: str = "16c941ae8b3d4c_210417_inv"
        response: SingleJson = manager.get_xql_search_results(query_id)

        assert type(response).__name__ == XQLSearchResult.__name__
        assert len(script_session.request_history) == 2

    def test_get_file_retrieval_details_success(
        self,
        manager: XDRManager,
        palo_alto_cortex_xdr: PaloAltoCortexXDR,
        script_session: PaloAltoCortexXDRSession,
    ) -> None:
        """Test get file retrieval details success. Verify that the get_file_retrieval_details method returns correct URL mappings when a valid group ID is provided."""
        group_id: str = '987654321'
        urls: FileRetrievalDetails = FileRetrievalDetails(
            raw_data={'data': {'ep1': 'https://api-root.com/public_api/v1/download/mysecrettoken'}},
            endpoint_url_map={'ep1': 'https://api-root.com/public_api/v1/download/mysecrettoken'},
        )
        palo_alto_cortex_xdr.add_file_retrieval_urls(group_id, urls)
        response: FileRetrievalDetails = manager.get_file_retrieval_details(group_id)
        assert type(response).__name__ == FileRetrievalDetails.__name__
        assert response.endpoint_url_map.get('ep1') == 'https://api-root.com/public_api/v1/download/mysecrettoken'
        assert len(script_session.request_history) == 2

    def test_retrieve_file_success(
        self,
        manager: XDRManager,
        palo_alto_cortex_xdr: PaloAltoCortexXDR,
        script_session: PaloAltoCortexXDRSession,
    ) -> None:
        """Test retrieve file success. Verify that the retrieve_file method returns the correct binary content when a valid download URL is provided."""
        download_url: str = 'https://api-root.com/public_api/v1/download/mysecrettoken'
        content: bytes = b'Zip content binary mock'
        palo_alto_cortex_xdr.add_file_content_by_val('mysecrettoken', content)
        response = manager.retrieve_file(download_url)
        assert response.content == content
        assert len(script_session.request_history) == 2
