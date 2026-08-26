# Copyright 2025 Google LLC
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
import re
from datetime import date, datetime

import whois_alt.parse as parse
from ipwhois import IPWhois
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
    dict_to_flat,
    output_handler,
)
from TIPCommon.data_models import CreateEntity
from TIPCommon.rest.soar_api import create_entity
from tldextract import extract

from ..core.data_model import get_domain_whois
from ..core.IpLocation import DbIpCity

# Monkeypatch whois_alt to prevent catastrophic backtracking on AFNIC (nic.fr) whois contacts
# filter out problematic AFNIC regexes
safe_regexes = []
for r in parse.nic_contact_regexes:
    pattern = r.pattern
    if "type:\\s*(?P<type>.+)" in pattern and "contact:\\s*(?P<name>.+)" in pattern:
        pass
    else:
        safe_regexes.append(r)
parse.nic_contact_regexes = safe_regexes


# add robust AFNIC parser fallback
def parse_afnic_contact_blocks(data):
    handle_contacts = []
    for segment in data:
        blocks = segment.split("\n\n")
        for block in blocks:
            if "nic-hdl:" not in block:
                continue
            contact = {}
            address_lines = []
            for line in block.splitlines():
                line = line.strip()
                if not line or ":" not in line:
                    continue
                key, val = line.split(":", 1)
                key = key.strip().lower()
                val = val.strip()
                if key == "nic-hdl":
                    contact["handle"] = val
                elif key == "type":
                    contact["type"] = val
                elif key == "contact":
                    contact["name"] = val
                elif key == "address":
                    address_lines.append(val)
                elif key == "country":
                    contact["country"] = val
                elif key == "phone":
                    contact["phone"] = val
                elif key == "fax-no":
                    contact["fax"] = val
                elif key == "e-mail":
                    contact["email"] = val
                elif key == "changed":
                    contact["changedate"] = val

            for idx, addr in enumerate(address_lines[:4]):
                contact[f"street{idx + 1}"] = addr

            if "handle" in contact:
                handle_contacts.append(contact)
    return handle_contacts


orig_parse_nic_contact = parse.parse_nic_contact


def my_parse_nic_contact(data):
    contacts = orig_parse_nic_contact(data)
    afnic_contacts = parse_afnic_contact_blocks(data)
    existing_handles = {c["handle"] for c in contacts if "handle" in c}
    for ac in afnic_contacts:
        if ac["handle"] not in existing_handles:
            contacts.append(ac)
            existing_handles.add(ac["handle"])
    return contacts


parse.parse_nic_contact = my_parse_nic_contact


SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.DOMAIN,
    EntityTypes.HOSTNAME,
    EntityTypes.URL,
    EntityTypes.USER,
]


def create_entity_with_relation(siemplify, new_entity, linked_entity):
    entity_to_create = CreateEntity(
        case_id=siemplify.case_id,
        alert_identifier=siemplify.alert_id,
        entity_type="DOMAIN",
        entity_identifier=new_entity.upper(),
        entity_to_connect_regex=f"{re.escape(linked_entity.upper())}$",
        types_to_connect=[],
    )
    create_entity(siemplify, entity_to_create)


def get_alert_entities(siemplify):
    return [entity for alert in siemplify.case.alerts for entity in alert.entities]


def get_domain_from_string(identifier):
    reg = extract(identifier.lower())
    return reg.registered_domain


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


@output_handler
def main():
    siemplify = SiemplifyAction()

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = None
    siemplify.script_name = "Whois"
    create_entities = (
        siemplify.extract_action_param("Create Entities", print_value=True).lower()
        == "true"
    )
    age_threshold = siemplify.extract_action_param(
        "Domain Age Threshold",
        print_value=True,
        default_value=0,
        input_type=int,
    )
    json_result = {}
    updated_entities = []
    enriched_entities = {}
    successful_entities = []
    failed_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    if not suitable_entities:
        siemplify.LOGGER.info("No suitable entities were found to enrich.")
        output_message = "No suitable entities were found to enrich."
        result_value = "false"
    else:
        for entity in suitable_entities:
            if entity.entity_type == EntityTypes.ADDRESS:
                try:
                    obj = IPWhois(entity.identifier)
                    obj.lookup_rdap(depth=1)
                    ip_whois = obj.lookup_rdap(depth=1)
                    response = DbIpCity.get(entity.identifier, api_key="free")
                    ip_whois["geo_lookup"] = json.loads(response.to_json())
                    json_result[entity.identifier] = ip_whois
                    enriched_entities[entity.identifier] = ip_whois
                    successful_entities.append(entity.identifier)
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed RDAP lookup for entity {entity.identifier}: {e}"
                    )
                    failed_entities.append(entity.identifier)
            else:
                try:
                    domain = get_domain_from_string(entity.identifier)
                    if domain:
                        whois_data = get_domain_whois(domain, logger=siemplify.LOGGER)
                        if "creation_date" in whois_data:
                            whois_data["age_in_days"] = int(
                                (
                                    datetime.now() - whois_data["creation_date"][0]
                                ).total_seconds()
                                / 86400,
                            )
                        json_result[entity.identifier] = json.loads(
                            json.dumps(whois_data, default=json_serial),
                        )
                        del whois_data["raw"]
                        enriched_entities[entity.identifier] = json.loads(
                            json.dumps(whois_data, default=json_serial),
                        )
                        successful_entities.append(entity.identifier)
                        if create_entities and domain.upper() != entity.identifier:
                            create_entity_with_relation(
                                siemplify,
                                domain,
                                entity.identifier,
                            )
                            enriched_entities[domain] = json.loads(
                                json.dumps(whois_data, default=json_serial),
                            )
                            json_result[domain] = json.loads(
                                json.dumps(whois_data, default=json_serial),
                            )
                    else:
                        failed_entities.append(entity.identifier)
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed WHOIS lookup for entity {entity.identifier}: {e}"
                    )
                    failed_entities.append(entity.identifier)

        if enriched_entities:
            siemplify.load_case_data()
            alert_entities = get_alert_entities(siemplify)
            for new_entity in enriched_entities:
                for entity in alert_entities:
                    if new_entity.strip() == entity.identifier.strip():
                        entity.additional_properties.update(
                            add_prefix_to_dict(
                                dict_to_flat(enriched_entities[new_entity]),
                                "WHOIS",
                            ),
                        )
                        if (
                            "age_in_days" in enriched_entities[new_entity]
                            and enriched_entities[new_entity]["age_in_days"]
                            < int(age_threshold)
                            and int(age_threshold) != 0
                        ):
                            if create_entities and entity.entity_type == EntityTypes.DOMAIN:
                                entity.is_suspicious = True

                            elif not create_entities:
                                entity.is_suspicious = True
                                siemplify.LOGGER.info(
                                    f"Marking {entity.identifier} as suspicious",
                                )
                        entity.is_enriched = True
                        updated_entities.append(entity)
                        break
            siemplify.LOGGER.info(f"updating entities: {updated_entities}")
            siemplify.update_entities(updated_entities)

        if successful_entities:
            output_message = f"Successfully enriched the following entities: {', '.join(successful_entities)}"
            result_value = "true"
        else:
            output_message = "No entities were enriched."
            result_value = "false"

        if failed_entities:
            output_message += f"\nFailed to enrich the following entities: {', '.join(failed_entities)}"

    return_json = json.dumps(json_result, default=json_serial)
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(return_json))

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
