from __future__ import annotations

from typing import TYPE_CHECKING

import requests
from urllib.parse import urljoin

from soar_sdk.SiemplifyDataModel import EntityTypes

from .constants import (
    COMPLETED_QUERY,
    DEFAULT_LIMIT,
    ENDPOINTS,
    ENTITIES_LOCATION,
    FILTER_KEY_VALUES,
    FILTER_LOGIC_OPERATORS,
    UPDATE_ACTIONS,
)
from .FortigateParser import FortigateParser
from .UtilsManager import (
    validate_response,
    transform_ip_address,
    remove_subnet_from_ip_address,
    get_domain_from_entity,
    filter_old_alerts,
)

if TYPE_CHECKING:
    from .datamodels import ThreatLog


class FortigateManager:
    def __init__(self, api_root, api_key, verify_ssl=False, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Fortigate API root
        :param api_key: {str} Fortigate API key
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.session = requests.session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        self.session.verify = verify_ssl
        self.parser = FortigateParser()
        self.sensitive_data_arr = [self.api_key]

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
        Test connectivity
        """
        url = self._get_full_url("ping")
        response = self.session.get(url)
        validate_response(response, self.sensitive_data_arr)

    def get_policy_by_name(self, policy_name):
        """
        Get policy by name
        :param policy_name: {str} Policy name
        :return: {list} List of Policy objects
        """
        url = self._get_full_url("get_policy_by_name", policy_name=policy_name)
        response = self.session.get(url)
        validate_response(response, self.sensitive_data_arr)
        return self.parser.build_policy_objects(response.json())

    def update_policy_entities(
        self, policy, items, entity_name, location, action=UPDATE_ACTIONS.get("add")
    ):
        """
        Add/Remove entities from policy
        :param policy: {Policy} Policy object
        :param items: {list} List of entities
        :param entity_name: {str} Provided entity name
        :param location: {str} Specifies the location for the entities - destination/source
        :param action: {str} Action that needs to be done - add/remove
        :return: {list} List of policy entities
        """
        if action == UPDATE_ACTIONS.get("add"):
            items.append({"name": entity_name, "q_origin_key": entity_name})
        else:
            index = next(
                (
                    index
                    for (index, item) in enumerate(items)
                    if item.get("name") == entity_name
                ),
                None,
            )
            items.pop(index)

        payload = {
            (
                "dstaddr"
                if location == ENTITIES_LOCATION.get("destination")
                else "srcaddr"
            ): items
        }

        url = self._get_full_url(
            "update_policy",
            policy_id=policy.id,
            policy_name=policy.name,
        )
        response = self.session.put(url, json=payload)
        validate_response(response, self.sensitive_data_arr)
        return items

    def get_entity(self, entity):
        """
        Get entity
        :param entity: {SiemplifyEntity} Siemplify entity object
        :return: {Entity} Entity object
        """
        if entity.entity_type == EntityTypes.ADDRESS:
            params = {"filter": f"subnet=={transform_ip_address(entity.identifier)}"}
        else:
            params = {"filter": f"fqdn=={get_domain_from_entity(entity.identifier)}"}

        url = self._get_full_url("get_address")
        response = self.session.get(url, params=params)
        validate_response(response, self.sensitive_data_arr)
        return self.parser.build_entity_objects(response.json())

    def create_entity(self, entity):
        """
        Create entity
        :param entity: {SiemplifyEntity} Siemplify entity object
        :return: {void}
        """
        if entity.entity_type == EntityTypes.ADDRESS:
            payload = {
                "name": remove_subnet_from_ip_address(entity.identifier),
                "subnet": transform_ip_address(entity.identifier),
            }
        else:
            domain = get_domain_from_entity(entity.identifier)
            payload = {"name": domain, "type": "fqdn", "fqdn": domain}

        url = self._get_full_url("create_address")
        response = self.session.post(url, json=payload)
        validate_response(response, self.sensitive_data_arr)

    def get_address_group_by_name(self, address_group_name):
        """
        Get address group by name
        :param address_group_name: {str} Address group name
        :return: {list} List of AddressGroup objects
        """
        url = self._get_full_url(
            "get_address_group_by_name",
            address_group_name=address_group_name,
        )
        response = self.session.get(url)
        validate_response(response, self.sensitive_data_arr)
        return self.parser.build_address_group_objects(response.json())

    def update_address_group_entities(
        self, address_group, items, entity_name, action=UPDATE_ACTIONS.get("add")
    ):
        """
        Add/Remove entities from address group
        :param address_group: {AddressGroup} AddressGroup object
        :param items: {list} List of entities
        :param entity_name: {str} Provided entity name
        :param action: {str} Action that needs to be done - add/remove
        :return: {list} List of address group entities
        """
        if action == UPDATE_ACTIONS.get("add"):
            items.append({"name": entity_name, "q_origin_key": entity_name})
        else:
            index = next(
                (
                    index
                    for (index, item) in enumerate(items)
                    if item.get("name") == entity_name
                ),
                None,
            )
            items.pop(index)

        payload = {"member": items}

        url = self._get_full_url(
            "update_address_group",
            address_group_name=address_group.name,
        )
        response = self.session.put(url, json=payload)
        validate_response(response, self.sensitive_data_arr)
        return items

    def list_policies(self, filter_key, filter_logic, filter_value, limit):
        """
        Get policies
        :param filter_key: {str} Filter key to use for results filtering
        :param filter_logic: {str} Filter logic
        :param filter_value: {str} Filter value
        :param limit: {str} Limit for results
        :return: {list} List of Policy objects
        """
        params = {"count": limit}

        if filter_value:
            params["filter"] = (
                f"{FILTER_KEY_VALUES.get(filter_key)}{FILTER_LOGIC_OPERATORS.get(filter_logic)}{filter_value}"
            )

        url = self._get_full_url("get_policies")
        response = self.session.get(url, params=params)
        validate_response(response, self.sensitive_data_arr)
        return self.parser.build_policy_objects(response.json())

    def list_address_groups(self, filter_key, filter_logic, filter_value, limit):
        """
        Get address groups
        :param filter_key: {str} Filter key to use for results filtering
        :param filter_logic: {str} Filter logic
        :param filter_value: {str} Filter value
        :param limit: {str} Limit for results
        :return: {list} List of AddressGroup objects
        """
        params = {"count": limit}

        if filter_value:
            params["filter"] = (
                f"{FILTER_KEY_VALUES.get(filter_key)}{FILTER_LOGIC_OPERATORS.get(filter_logic)}{filter_value}"
            )

        url = self._get_full_url("get_address_groups")
        response = self.session.get(url, params=params)
        validate_response(response, self.sensitive_data_arr)
        return self.parser.build_address_group_objects(response.json())

    def get_threat_logs(
        self,
        existing_ids: list[str],
        limit: int,
        start_timestamp: str,
        subtype: str,
        severity_filter: list[str] | None = None,
        location: str | None = None,
        vdom: str | None = None,
        serial_number: str | None = None,
    ) -> list[ThreatLog]:
        """Get threat logs.

        Args:
            existing_ids: The ids of already existing alerts.
            limit: The maximum number of alerts to fetch.
            start_timestamp: The timestamp from which to fetch alerts.
            subtype: The subtype of threat logs to fetch.
            severity_filter: The list of severities to filter by.
            location: The location of the threat logs.
            vdom: The VDOM to filter by.
            serial_number: The serial number to filter by.

        Returns:
            A list of ThreatLog objects.
        """
        request_url = self._get_full_url(
            "get_threat_logs",
            location=location if location is not None else "disk",
            subtype=subtype,
        )
        if location == "memory":
            params = {"filter": [f"eventtime:[{start_timestamp} TO *]"], "rows": 1}
        else:
            params = {"filter": [f"eventtime>={start_timestamp}"], "rows": 1}
        if vdom is not None:
            params["vdom"] = vdom
        if serial_number is not None:
            params["serial_no"] = serial_number
        if severity_filter:
            params["filter"].append(
                ",".join([f"level=={severity}" for severity in severity_filter])
            )

        fetch_limit = max(DEFAULT_LIMIT, limit)
        completed = False

        # If query is not completed, we need to get to the point, where all the data is generated
        while not completed:
            response = self.session.get(request_url, params=params)
            validate_response(response)

            json_result = response.json()
            session_id = json_result.get("session_id", 0)
            total_lines = json_result.get("total_lines", 0)
            completed = (
                True if json_result.get("completed", 0) == COMPLETED_QUERY else False
            )
            start = max((total_lines - fetch_limit), 0) + 1

            params.update(
                {"rows": fetch_limit, "start": start, "session_id": session_id}
            )

        # In the end, we fetch only the last page, which are the oldest logs
        response = self.session.get(request_url, params=params)
        validate_response(response)

        logs = self.parser.build_threat_log_objects(response.json())

        filtered_logs = filter_old_alerts(
            logger=self.siemplify_logger, alerts=logs, existing_ids=existing_ids
        )
        return sorted(filtered_logs, key=lambda log: log.event_time)
