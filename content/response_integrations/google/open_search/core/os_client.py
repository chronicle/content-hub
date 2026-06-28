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
import base64
import json

from .constants import (
    CA_CERTIFICATE_FILE_PATH,
    DEFAULT_MAX_LIMIT,
    DEFAULT_TIMEOUT,
    DISPLAYFIELD,
    DSL_INDEX,
    OS_INDEX,
    OS_QUERY,
    OPENSEARCH_QUERY_JSON,
    SEARCHFIELD,
    TIMESTAMPFIELD,
)
from .data_models import IntegrationParameters
from .data_parser import OpenSearchParser
from .exceptions import OpenSearchManagerError
from opensearch_dsl import Q, Search
from opensearchpy import OpenSearch
from TIPCommon.base.interfaces import ScriptLogger
from TIPCommon.filters import filter_old_alerts
from TIPCommon.smp_time import is_approaching_timeout


class OpenSearchManager:
    """
    Responsible for all OpenSearch operations functionality
    """

    def __init__(
        self,
        integration_parameters: IntegrationParameters,
        logger: ScriptLogger,
    ) -> None:
        self.server: str = integration_parameters.server
        self.logger: ScriptLogger = logger
        self.es = self._authenticate(integration_parameters)
        self.parser = OpenSearchParser()

    def _authenticate(
        self,
        integration_parameters: IntegrationParameters,
    ) -> OpenSearch:
        if not self.server:
            raise OpenSearchManagerError("Server is not configured.")
        ca_certificate_file: str = integration_parameters.ca_certificate_file
        verify_ssl: bool = integration_parameters.verify_ssl
        authenticate: bool = integration_parameters.authenticate
        username: str = integration_parameters.username
        password: str = integration_parameters.password
        jwt_token: str = integration_parameters.jwt_token

        ca_certs = False if not verify_ssl else None
        if ca_certificate_file:
            try:
                file_content = base64.b64decode(ca_certificate_file)
                with open(CA_CERTIFICATE_FILE_PATH, "w+", encoding="utf-8") as f:
                    f.write(file_content.decode("utf-8"))

            except Exception as e:
                raise OpenSearchManagerError(e) from e

        if verify_ssl and ca_certificate_file:
            ca_certs = CA_CERTIFICATE_FILE_PATH

        if jwt_token:
            return OpenSearch(
                [self.server],
                api_key=(jwt_token),
                ca_certs=ca_certs,
                verify_certs=verify_ssl,
                timeout=DEFAULT_TIMEOUT,
            )
        if username and password:
            return OpenSearch(
                [self.server],
                http_auth=(username, password),
                ca_certs=ca_certs,
                verify_certs=verify_ssl,
                timeout=DEFAULT_TIMEOUT,
            )
        if authenticate and not username and not password and not jwt_token:
            raise OpenSearchManagerError(
                "Please specify username and password or JWT token."
            )

        return OpenSearch(
            [self.server],
            verify_certs=verify_ssl,
            ca_certs=ca_certs,
            timeout=DEFAULT_TIMEOUT,
        )

    def test_connectivity(self):
        """Test connectivity to the OpenSearch server.

        Returns:
            bool: True if the connection is successful.
        """
        self.es.info()
        return True

    def advanced_os_search(self, **kwargs):
        """
        Run an advanced query with specific parameters.

        Args:
            **kwargs: Arbitrary keyword arguments. The following are supported:
                Index (str): Index name to search.
                Query (str): Lucene query string syntax.
                Display Field (str): Returned fields.
                Search Field (str): Default field for querying terms.
                Timestamp Field (str): The field to use for time-based filtering.
                Oldest Date (str): Start date of search.
                Earliest Date (str): End date of search.
                Limit (int): Number of results to return.
                Existing IDs (list): List of existing ids to filter by.

        Returns:
            tuple[list, bool, int]: A tuple containing the list of results,
                the status of the search, and the total number of hits.
        """
        s_index = kwargs.get("Index", OS_INDEX)
        s_query = kwargs.get("Query", OS_QUERY)
        display_field = kwargs.get("Display Field", DISPLAYFIELD)
        search_field = kwargs.get("Search Field", SEARCHFIELD)
        timestamp_field = kwargs.get("Timestamp Field", TIMESTAMPFIELD)
        oldest_date_compare_type = kwargs.get("Oldest Date Compare Type", "gt")
        eariest_date_compare_type = kwargs.get("Earliest Date Compare Type", "lt")
        oldest_date = kwargs.get("Oldest Date")
        earliest_date = kwargs.get("Earliest Date")
        limit = kwargs.get("Limit")
        existing_ids = kwargs.get("Existing IDs", [])

        s = Search(using=self.es, index=s_index).query(
            "query_string", default_field=search_field, query=s_query
        )

        if oldest_date and earliest_date:
            s = s.query(
                Q(
                    "range",
                    **{
                        timestamp_field: {
                            oldest_date_compare_type: oldest_date,
                            eariest_date_compare_type: earliest_date,
                        }
                    },
                )
            )

        elif oldest_date:
            s = s.query(
                Q("range", **{timestamp_field: {oldest_date_compare_type: oldest_date}})
            )

        elif earliest_date:
            s = s.query(
                Q(
                    "range",
                    **{timestamp_field: {eariest_date_compare_type: earliest_date}},
                )
            )

        s = s.sort({timestamp_field: {"missing": "_last", "unmapped_type": "date"}})

        if existing_ids:
            s = s.exclude("ids", values=existing_ids)

        s = s.source(display_field)

        if limit:
            s = s.extra(from_=0, size=limit)
        else:
            s = s.extra(from_=0, size=s.count())

        response = s.execute()
        if not response.success():
            raise OpenSearchManagerError(
                f"OpenSearch query failed: {response.to_dict()}"
            )

        status = True
        total_hits = response.hits.total.get("value")
        results = response.to_dict()

        return results["hits"]["hits"], status, total_hits

    def simple_os_search(self, s_index=OS_INDEX, query=OS_QUERY, limit=None):
        """Run a simple Lucene formatted query.

        Args:
            s_index (str, optional): Index name to search. Defaults to OS_INDEX.
            query (str, optional): Lucene query string syntax. Defaults to OS_QUERY.
            limit (int, optional): Number of results to return. Defaults to None.

        Returns:
            tuple[list, bool, int]: A tuple containing the list of results,
                the status of the search, and the total number of hits.
        """

        if s_index is None:
            s_index = OS_INDEX

        if query is None:
            query = OS_QUERY

        s = Search(using=self.es, index=s_index).query("query_string", query=query)

        if limit:
            s = s.extra(from_=0, size=limit)
        else:
            s = s.extra(from_=0, size=s.count())

        response = s.execute()
        status = response.success()
        total_hits = response.hits.total.get("value")
        results = response.to_dict()

        return results["hits"]["hits"], status, total_hits

    def dsl_search(
        self,
        chronicle_soar,
        indices=DSL_INDEX,
        query=None,
        max_results=10,
        existing_ids=None,
        connector_start_time=None,
        python_process_timeout=None,
    ):
        """Run a DSL query search.

        Args:
            chronicle_soar: The Chronicle SOAR object.
            indices (str, optional): Index name to search. Defaults to DSL_INDEX.
            query (str, optional): DSL Query. Defaults to None.
            max_results (int, optional): The limit of search count. Defaults to 10.
            existing_ids (list, optional): List of existing ids to filter out.
                Defaults to None.
            connector_start_time (int, optional): Connector start time for timeout
                calculation. Defaults to None.
            python_process_timeout (int, optional): The script timeout in seconds.
                Defaults to None.

        Returns:
            tuple[list, dict]: A tuple containing the list of results and total hits.
        """

        if query == OS_QUERY:
            query = OPENSEARCH_QUERY_JSON.copy()
        else:
            try:
                query = json.loads(query)
            except Exception as e:
                raise OpenSearchManagerError(e) from e

            query = {"query": query}

        filtered_results = []
        from_ = 0
        limit = max_results
        total_hits = {}

        while len(filtered_results) < max_results:
            if from_ >= total_hits.get("value", DEFAULT_MAX_LIMIT):
                break
            if from_ + limit > total_hits.get("value", DEFAULT_MAX_LIMIT):
                limit = total_hits.get("value", DEFAULT_MAX_LIMIT) - from_

            timed_out = (
                connector_start_time
                and python_process_timeout
                and is_approaching_timeout(connector_start_time, python_process_timeout)
            )

            if timed_out:
                self.logger.info(
                    "Timeout is approaching. Connector will gracefully exit"
                )
                break

            self.logger.info(f"Executing DSL Search with query: {json.dumps(query)}")
            result = self.es.search(index=indices, from_=from_, size=limit, body=query)
            hits = result.get("hits", {}).get("hits", [])
            total_hits = result.get("hits", {}).get("total", {})

            if not hits:
                break

            results = self.parser.build_dsl_result_objects(hits)

            self.logger.info(
                f"Fetched {len(results)} search results, with from {from_}."
            )

            if existing_ids is not None:
                filtered_results.extend(
                    filter_old_alerts(
                        chronicle_soar, alerts=results, existing_ids=existing_ids
                    )
                )
            else:
                filtered_results.extend(results)

            from_ += limit

        filtered_results = filtered_results[:max_results]
        self.logger.info(f"Found {len(filtered_results)} new results.")

        return filtered_results, total_hits
