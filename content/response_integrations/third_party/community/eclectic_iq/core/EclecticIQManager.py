from __future__ import annotations

import uuid

import requests
from soar_sdk.SiemplifyDataModel import EntityTypes

from .EclecticIQParser import EclecticIQLookupParser

ENDPOINT = {
    "get_observables": "/api/v2/observables",
    "get_entities": "/api/v2/entities",
    "get_sources": "/api/v2/sources",
    "test": "/api/v2/sources",
    "create_entities": "/api/v2/entities",
    "get_groups": "/private/groups/",
    "outgoing_feed_list": "/api/v2/outgoing-feeds?filter[content_type]=urn:eclecticiq.com:csv-extracts:1.0&filter[transport_type]=eiq.outgoing-transports.http-download&attributes=id&limit=500",
    "get_content_blocks": "/private/outgoing-feed-download/",
}

REQUEST_LENGTH = 3500

ENTITY_MAP = {
    EntityTypes.HOSTNAME: "host",
    EntityTypes.ADDRESS: "ipv4",
    EntityTypes.PROCESS: "process",
    EntityTypes.PARENTPROCESS: "process",
    EntityTypes.CHILDPROCESS: "process",
    EntityTypes.FILENAME: "file",
    EntityTypes.FILEHASH: "hash-sha256",
    EntityTypes.PARENTHASH: "hash-sha256",
    EntityTypes.CHILDHASH: "hash-sha256",
    EntityTypes.URL: "uri",
    EntityTypes.EMAILMESSAGE: "email",
    EntityTypes.CVEID: "cve",
    EntityTypes.CREDITCARD: "card",
    EntityTypes.PHONENUMBER: "telephone",
    EntityTypes.CVE: "cve",
    EntityTypes.THREATACTOR: "actor-id",
    EntityTypes.SOURCEDOMAIN: "domain",
    EntityTypes.DESTINATIONDOMAIN: "domain",
    EntityTypes.DOMAIN: "domain",
}


class EclecticIQManagerException(Exception):
    """General Exception for EclecticIQ manager"""


class EclecticIQManager:
    def __init__(self, eiq_url, api_token, verify_ssl=False):
        self.eiq_url = eiq_url
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        # self.session.verify = verify_ssl
        self.session.headers.update(
            {"Accept": "application/json", "Authorization": f"Bearer {self.api_token}"},
        )

    def test_connectivity(self):
        try:
            url = self.eiq_url + ENDPOINT["test"]
            response = self.session.get(url)
            self.validate_response(response)
        except Exception as e:
            raise EclecticIQManagerException(
                f"Unable to connect to EclecticIQ. Please validate your credentials. Error: {e}",
            )

    def get_source(self, url):
        response = self.session.get(url)
        return response.json()["data"]["name"]

    def batch_filter_bulk_call(self, values: list, endpoint, filter_name):
        def fetch_data(filters):
            url = f"{self.eiq_url}{endpoint}?{'&'.join(filters)}"
            response = self.session.get(url)
            self.validate_response(response)
            return response.json().get("data", [])

        results = []
        current_filters = []
        current_length = 0

        try:
            for value in values:
                filter_value = f"filter[{filter_name}]={value}"
                # +1 accounts for the '&' character used to join filters in a URL
                if current_length + len(filter_value) + 1 <= REQUEST_LENGTH:
                    current_filters.append(filter_value)
                    current_length += len(filter_value) + 1
                else:
                    results.extend(fetch_data(current_filters))
                    current_filters = [filter_value]
                    current_length = len(filter_value)

            # Handle any remaining filters
            if current_filters:
                results.extend(fetch_data(current_filters))

            return results

        except Exception as e:
            raise EclecticIQManagerException(
                f"Unable to Enrich the Entities. Error: {e}",
            )

    def fetch_observables_info(self, values: list) -> list:
        return self.batch_filter_bulk_call(values, ENDPOINT["get_observables"], "value")

    def fetch_entities_info(self, values: list) -> list:
        return self.batch_filter_bulk_call(
            values,
            ENDPOINT["get_entities"],
            "observables",
        )

    def update_sources_in_eiq_entities(self, eiq_entities):
        url = self.eiq_url + ENDPOINT["get_sources"]
        response = self.session.get(url)
        self.validate_response(response)
        sources = response.json().get("data", [])
        source_id_to_name = {source["id"]: source.get("name") for source in sources}

        for entity in eiq_entities:
            source_ids = {source.split("/")[-1] for source in entity.get("sources", [])}
            entity["sources"] = [
                source_id_to_name.get(sid)
                for sid in source_ids
                if sid in source_id_to_name
            ]
        return eiq_entities

    def enrich(self, original_entities) -> EclecticIQLookupParser:
        identifiers = [str(entity.identifier.lower()) for entity in original_entities]
        eiq_observables = self.fetch_observables_info(identifiers)
        observable_ids = [obs["id"] for obs in eiq_observables if obs.get("id")]

        eiq_entities = self.fetch_entities_info(observable_ids)

        eiq_entities = self.update_sources_in_eiq_entities(eiq_entities)

        return EclecticIQLookupParser(
            eiq_observables=eiq_observables,
            eiq_entities=eiq_entities,
            original_entities=original_entities,
            eiq_url=self.eiq_url,
        )

    def get_group_source_id(self, group_name):
        response = self.session.get(
            self.eiq_url + ENDPOINT["get_groups"],
            params=f"filter[name]={group_name}",
        )
        self.validate_response(response)
        return response.json()["data"][0]["source"]

    def create_entities(self, case, entities, group_name, create_indicator=False):
        source_id = self.get_group_source_id(group_name)
        url = self.eiq_url + ENDPOINT["create_entities"]
        _id = f"indicator-{uuid.uuid5(uuid.NAMESPACE_X500, case.identifier)!s}"

        description_field = [
            ("Case Title", case.title),
            ("Case Description", case.description),
            ("Priority", case.priority),
            ("Is Important", case.is_important),
            ("Status", case.status),
            ("Stage", case.stage),
            ("Has Suspicious Entity", case.has_suspicious_entity),
            ("High Risk Products", case.high_risk_products),
            ("Start Time", case.start_time),
            ("Sla Expiration Unix Time", case.sla_expiration_unix_time),
            ("Is Incident", case.is_incident),
        ]

        description = ""

        for title, value in description_field:
            if value is not None:
                description += f"<p><strong>{title}:</strong> {value}</p>"

        sighting = {
            "data": {
                "title": case.title,
                "type": "eclecticiq-sighting",
                "description": description,
                "id": f"eclecticiq-sighting-{uuid.uuid5(uuid.NAMESPACE_X500, case.identifier)!s}",
                "extracts": [
                    {
                        "kind": ENTITY_MAP[entity.entity_type],
                        "value": entity.identifier.lower(),
                    }
                    for entity in entities
                    if entity.entity_type in ENTITY_MAP
                ],
            },
            "meta": {"tags": ["Chronicle SOAR"]},
            "sources": [{"source_id": source_id}],
        }
        data = [sighting]
        if create_indicator:
            data.append(
                {
                    "data": {
                        "title": case.title,
                        "type": "indicator",
                        "description": description,
                        "id": f"indicator-{uuid.uuid5(uuid.NAMESPACE_X500, case.identifier)!s}",
                        "extracts": [
                            {
                                "kind": ENTITY_MAP[entity.entity_type],
                                "value": entity.identifier.lower(),
                            }
                            for entity in entities
                            if entity.entity_type in ENTITY_MAP
                        ],
                    },
                    "meta": {"tags": ["Chronicle SOAR"]},
                    "sources": [{"source_id": source_id}],
                },
            )

        response = self.session.put(url, json={"data": data})
        self.validate_response(response)
        return response.json()

    def validate_feeds(self, outgoing_feed_id):
        url = self.eiq_url + ENDPOINT["outgoing_feed_list"]
        response = self.session.get(url)
        self.validate_response(response)
        feeds = response.json().get("data", [])
        for feed in feeds:
            if str(feed.get("id")) == str(outgoing_feed_id):
                return True

        raise EclecticIQManagerException("Invalid Outgoing Feed ID")

    def get_content_block_data(self, content_block_url):
        url = self.eiq_url + content_block_url
        response = self.session.get(url)
        self.validate_response(response)
        return self.parse_csv(response.text)

    def parse_csv(self, text):
        lines = text.strip().split("\r\n")  # Split the text into lines
        if len(lines) < 2:
            return []

        header = lines[0].split(",")
        result = []

        for line in lines[1:]:
            curr = {}
            for col, val in enumerate(line.split(",")):
                if col < len(header):
                    curr[header[col]] = val
            result.append(curr)
        return result

    def get_content_blocks(self, outgoing_feed_id):
        url = self.eiq_url + ENDPOINT["get_content_blocks"] + str(outgoing_feed_id)
        response = self.session.get(url)
        self.validate_response(response)
        content_blocks = response.json().get("data", {}).get("content_blocks", [])
        return content_blocks

    @staticmethod
    def validate_response(response):
        """Check if request response is ok"""
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise EclecticIQManagerException(f"{e}. {response.text}")
