from __future__ import annotations
from urllib.parse import urljoin
import requests
from .constants import (
    ENDPOINTS,
    BLOCK_ACTION,
    ALLOW_ACTION,
    ALL_ITEMS_STRING,
    DATETIME_ISO_FORMAT,
    DATETIME_API_FORMAT,
)
from .UtilsManager import validate_response
from .AlgoSecParser import AlgoSecParser
import datetime
import json


class AlgoSecManager:
    def __init__(
        self, api_root, username, password, verify_ssl=False, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API root of the AlgoSec instance.
        :param username: {str} Username of the AlgoSec account.
        :param password: {str} Password of the AlgoSec account.
        :param verify_ssl: {bool} If enabled, verify the SSL certificate for the connection to the AlgoSec server is valid.
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password
        self.logger = siemplify_logger
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = AlgoSecParser()
        self.session_id = self._generate_session()
        self.session.headers.update({"Cookie": f"FireFlow_Session={self.session_id}"})

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _generate_session(self):
        """
        :return: {string} Session ID
        """
        request_url = self._get_full_url("authentication")
        payload = {"username": self.username, "password": self.password, "domain": None}
        res = self.session.post(request_url, json=payload)
        validate_response(res)
        return res.json().get("data", {}).get("sessionId")

    def test_connectivity(self):
        """
        Test connectivity
        """
        request_url = self._get_full_url("ping")
        response = self.session.get(request_url)
        validate_response(response)

    def create_request(
        self,
        ip_addresses,
        template,
        source,
        service,
        subject,
        owner,
        due_date,
        expiration_date,
        custom_fields,
        is_block=False,
    ):
        """
        :param ip_addresses: {list} List of destination IP addresses
        :param template: {str} The template name for request
        :param source: {list} List of sources
        :param service: {list} List of services
        :param subject: {str} The subject for request
        :param owner: {str} The owner of request
        :param due_date: {str} The due date of request
        :param expiration_date: {str} The expiration date of request
        :param custom_fields: {dict} Custom fields to add to request
        :param is_block: {bool} Is block or allow action
        :return: {RequestObject}
        """
        request_url = self._get_full_url("create_request")
        payload = self._create_request_body(
            ip_addresses,
            template,
            source,
            service,
            subject,
            owner,
            due_date,
            expiration_date,
            custom_fields,
            is_block,
        )
        response = self.session.post(request_url, json=payload)
        validate_response(response)

        return self.parser.build_request_object(response.json())

    def get_request_details(self, request_id):
        """
        :param request_id: {int} Id of the request to return
        :return: {RequestObject}
        """
        request_url = self._get_full_url("get_request_details", request_id=request_id)
        response = self.session.get(request_url)
        validate_response(response)

        return self.parser.build_request_object(response.json())

    def _create_request_body(
        self,
        ip_addresses,
        template,
        source,
        service,
        subject,
        owner,
        due_date,
        expiration_date,
        custom_fields,
        is_block,
    ):
        source_items = []
        destination_items = []
        service_items = []
        fields = []

        if ALL_ITEMS_STRING in source:
            source_items.append({"address": ALL_ITEMS_STRING})
        else:
            for src in source:
                source_items.append({"address": src})

        for ip_address in ip_addresses:
            destination_items.append({"address": ip_address})

        if ALL_ITEMS_STRING in service:
            service_items.append({"service": ALL_ITEMS_STRING.upper()})
        else:
            for srv in service:
                service_items.append({"service": srv})

        if custom_fields:
            try:
                custom_fields_json = json.loads(custom_fields).items()
            except Exception:
                raise Exception(
                    "Invalid JSON object provided. Please check the structure."
                )

            for key, value in custom_fields_json:
                fields.append({"name": key, "values": [value]})
        else:
            if subject:
                fields.append({"name": "Subject", "values": [subject]})
            if owner:
                fields.append({"name": "Owner", "values": [owner]})
            if due_date:
                fields.append(
                    {
                        "name": "Due",
                        "values": [
                            datetime.datetime.strptime(
                                due_date, DATETIME_ISO_FORMAT
                            ).strftime(DATETIME_API_FORMAT)
                        ],
                    }
                )
            if expiration_date:
                fields.append(
                    {
                        "name": "Expires",
                        "values": [
                            datetime.datetime.strptime(
                                expiration_date, DATETIME_ISO_FORMAT
                            ).strftime(DATETIME_API_FORMAT)
                        ],
                    }
                )

        return {
            "template": template,
            "fields": fields,
            "traffic": [
                {
                    "source": {"items": source_items},
                    "destination": {"items": destination_items},
                    "service": {"items": service_items},
                    "application": {},
                    "user": {},
                    "action": BLOCK_ACTION if is_block else ALLOW_ACTION,
                }
            ],
        }

    def list_templates(self):
        """
        List all available templates
        :return: {list} List of Template objects
        """
        request_url = self._get_full_url("list_templates")
        response = self.session.get(request_url)
        validate_response(response, "Unable to list templates")

        return self.parser.build_templates_list(response.json())
