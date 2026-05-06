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
import json
import uuid
from urllib.parse import urljoin
import requests
from .constants import ENDPOINTS, NAME_DEFAULT_STRUCTURE
from .UtilsManager import validate_response, get_dict_from_string, get_ip_type
from .CiscoOrbitalParser import CiscoOrbitalParser
from soar_sdk.SiemplifyDataModel import EntityTypes


class CiscoOrbitalManager:
    def __init__(
        self, api_root, client_id, client_secret, verify_ssl=True, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API root of the Cisco Orbital instance.
        :param client_id: Client ID of the Cisco Orbital account.
        :param client_secret: Client Secret of the Cisco Orbital account.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the Cisco Orbital server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = CiscoOrbitalParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.set_auth_token()

    def set_auth_token(self):
        """
        Set Authorization header to request session.
        """
        self.session.headers.update(
            {"Authorization": f"Bearer {self.get_auth_token()}"}
        )

    def get_auth_token(self):
        """
        Send request in order to generate token.
        :return: {str} The authorization token
        """
        url = self._get_full_url("generate_token")
        response = self.session.post(url, auth=(self.client_id, self.client_secret))
        validate_response(response)
        return self.parser.get_auth_token(response.json())

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to the Cisco Orbital.
        :return: {void}
        """
        url = self._get_full_url("test_connectivity")
        response = self.session.get(url)
        validate_response(response, "Unable to connect to Cisco Orbital.")

    def submit_query(self, entities, query, name, context, expiration_unix=None):
        """
        Submit the query on endpoints.
        :param entities: {list} The list of entities.
        :param query: {str} The query that needs to be executed.
        :param name: {str} The name for the query job.
        :param context: {str} The additional custom context fields that should be added to the job.
        :param expiration_unix: {int} Unix epoch time the query will expire
        :return: {str} The query job id.
        """
        url = self._get_full_url("submit_query")
        payload = {
            "name": name or NAME_DEFAULT_STRUCTURE.format(str(uuid.uuid4())),
            "nodes": self.get_nodes_from_entities(entities),
            "expiry": expiration_unix,
            "osQuery": [{"sql": query}],
            "interval": 0,
            "context": get_dict_from_string(context) if context else {},
        }

        response = self.session.post(url, json.dumps(payload))
        validate_response(response)
        return self.parser.get_job_id(response.json())

    def get_nodes_from_entities(self, entities):
        """
        Get nodes on which queries will be executed.
        :param entities: {list} The list of entities.
        :return: {list} The list of nodes.
        """
        nodes = []

        for entity in entities:
            if entity.entity_type == EntityTypes.HOSTNAME:
                nodes.append(f"host:{entity.identifier}")
            if entity.entity_type == EntityTypes.ADDRESS and get_ip_type(
                entity.identifier
            ):
                nodes.append(f"{get_ip_type(entity.identifier)}:{entity.identifier}")

        return nodes

    def get_endpoints_results(self, job_id, limit):
        """
        Get endpoints query results by job id.
        :param job_id: {str} The job id to fetch data.
        :param limit: {int} Maximum number of results rows.
        :return: {list} List of EndpointResult objects.
        """
        url = self._get_full_url("get_results", job_id=job_id)
        response = self.session.get(url)
        validate_response(response)
        return self.parser.get_endpoints_results(response.json(), limit)
