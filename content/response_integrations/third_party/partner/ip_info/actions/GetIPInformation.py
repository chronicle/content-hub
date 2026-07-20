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

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
    dict_to_flat,
    flat_dict_to_csv,
    output_handler,
)

from ..core.IPInfoManager import BATCH_MAX_IPS, IPInfoManager

ACTION_NAME = "IPInfo Get_IP_Information"
PROVIDER = "IPInfo"
INTEGRATION_PREFIX = "IPInfo"


def normalize_bundle_payload(ip_information):
    """
    Normalize a bundle response so it conforms to the unified JSON result schema.

    Bundles disagree on the type of the ``asn`` field: the Lite bundle returns it
    as a flat string (e.g. "AS13335") while the Legacy bundle returns it as an
    object. To keep a single JSON result schema (see
    resources/GetIPInformation_JsonResult_example.json) ``asn`` is always emitted
    as an object; the Lite string is folded into it alongside the flat
    ``as_name``/``as_domain`` fields. Core/Plus/Max expose AS data under a
    separate ``as`` object and are left untouched.

    Args:
        ip_information: Raw per-IP payload from IPInfo. Mutated in place.

    Returns:
        The same dict, with ``asn`` normalized to an object when needed.
    """
    asn = ip_information.get("asn")
    if isinstance(asn, str):
        ip_information["asn"] = {
            "asn": asn,
            "name": ip_information.get("as_name"),
            "domain": ip_information.get("as_domain"),
        }
    return ip_information


def enrich_legacy(ipinfo_manager, siemplify, ip_entities):
    """
    Enrich ADDRESS entities one-by-one via the IPInfo legacy per-IP endpoint.

    Each entity is queried independently. A failure on one entity is logged and
    appended to the returned errors list without aborting the loop.

    Args:
        ipinfo_manager: Configured IPInfoManager client. Uses get_ip_information.
        siemplify: SiemplifyAction context. Used for logging and to attach
            per-entity result tables.
        ip_entities: Target entities to enrich. Expected to be of type ADDRESS.

    Returns:
        A 3-tuple of:
            - json_results (dict): mapping of entity identifier to raw response
              payload, for each successfully enriched entity.
            - success_entities (list): entities whose additional_properties were
              updated and is_enriched set to True.
            - errors (list[str]): one human-readable message per failed entity.
    """
    success_entities = []
    errors = []
    json_results = {}

    for entity in ip_entities:
        try:
            ip_information = ipinfo_manager.get_ip_information(entity.identifier)
            if ip_information:
                json_results[entity.identifier] = ip_information
                flat_info = dict_to_flat(ip_information)
                entity.additional_properties.update(add_prefix_to_dict(flat_info, INTEGRATION_PREFIX))
                entity.is_enriched = True
                siemplify.result.add_entity_table(entity.identifier, flat_dict_to_csv(flat_info))
                success_entities.append(entity)
        except Exception as err:
            error_message = f"Failed fetching information for {entity.identifier}, ERROR: {err}"
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    return json_results, success_entities, errors


def enrich_batch(ipinfo_manager, siemplify, ip_entities, bundle):
    """
    Enrich ADDRESS entities via the IPInfo batch endpoint, chunked by BATCH_MAX_IPS.

    The input is split into chunks of at most BATCH_MAX_IPS entities. Each chunk
    is sent in a single POST. If a chunk request fails (network, HTTP error,
    malformed response) every entity in that chunk is marked as errored and the
    loop continues with the next chunk so successful chunks are preserved.
    Per-IP errors returned inside a successful response as {"error": "..."} are
    also collected.

    Args:
        ipinfo_manager: Configured IPInfoManager client. Uses get_ip_information_batch.
        siemplify: SiemplifyAction context. Used for logging and to attach
            per-entity result tables.
        ip_entities: Target entities to enrich. Expected to be of type ADDRESS.
        bundle: IPInfo bundle name. One of "Lite", "Core", "Plus", "Max".
            Selects which batch endpoint to call.

    Returns:
        A 3-tuple of:
            - json_results (dict): mapping of entity identifier to raw response
              payload, for each successfully enriched entity.
            - success_entities (list): entities whose additional_properties were
              updated and is_enriched set to True.
            - errors (list[str]): one human-readable message per failure
              (chunk-level or per-IP).
    """
    success_entities = []
    errors = []
    json_results = {}

    for i in range(0, len(ip_entities), BATCH_MAX_IPS):
        chunk_entities = ip_entities[i : i + BATCH_MAX_IPS]
        try:
            batch_results = ipinfo_manager.get_ip_information_batch(
                [entity.identifier for entity in chunk_entities], bundle
            )
        except Exception as err:
            for entity in chunk_entities:
                error_message = f"Failed fetching information for {entity.identifier}, ERROR: {err}"
                siemplify.LOGGER.error(error_message)
                errors.append(error_message)
            continue

        for entity in chunk_entities:
            ip_information = batch_results.get(entity.identifier)
            if not ip_information:
                continue

            if isinstance(ip_information, dict) and "error" in ip_information:
                error_message = f"Failed fetching information for {entity.identifier}, ERROR: {ip_information['error']}"
                siemplify.LOGGER.error(error_message)
                errors.append(error_message)
                continue
            elif not isinstance(ip_information, dict):
                error_message = (
                    f"Failed fetching information for {entity.identifier}, "
                    f"unexpected response type: {type(ip_information)}"
                )
                siemplify.LOGGER.error(error_message)
                errors.append(error_message)
                continue
            ip_information = normalize_bundle_payload(ip_information)
            json_results[entity.identifier] = ip_information
            flat_info = dict_to_flat(ip_information)
            entity.additional_properties.update(add_prefix_to_dict(flat_info, INTEGRATION_PREFIX))
            entity.is_enriched = True
            siemplify.result.add_entity_table(entity.identifier, flat_dict_to_csv(flat_info))
            success_entities.append(entity)

    return json_results, success_entities, errors


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(PROVIDER)
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    ipinfo_manager = IPInfoManager(conf["API Root"], conf["Token"], verify_ssl)

    success_entities = []
    errors = []
    json_results = {}

    ip_entities = [entity for entity in siemplify.target_entities if entity.entity_type == EntityTypes.ADDRESS]

    bundle = siemplify.extract_action_param(param_name="IPinfo Bundle", default_value="Legacy")

    if bundle == "Legacy":
        json_results, success_entities, errors = enrich_legacy(ipinfo_manager, siemplify, ip_entities)
    else:
        json_results, success_entities, errors = enrich_batch(ipinfo_manager, siemplify, ip_entities, bundle)

    siemplify.update_entities(success_entities)

    if success_entities:
        output_message = f"Fetched IP information for: {', '.join([entity.identifier for entity in success_entities])}"
    else:
        output_message = "No information fetched for target entities."

    if errors:
        output_message = "{0}\n\nErrors:\n{1}".format(output_message, "\n".join(errors))

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, len(success_entities) > 0)


if __name__ == "__main__":
    main()
