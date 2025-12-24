"""Enrich Asset Information Action."""

from typing import Any, Dict, List, Optional

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ApiManager import ApiManager
from ..core.constants import ERRORS, INTEGRATION_NAME
from ..core.utils import get_integration_params, validate_ip_address

# Configuration constants
PREFIX = "Cylus_"
MAX_LIST_ITEMS = 5

# Known list fields that should be treated as arrays
# These are the fields mentioned in the API docs that return arrays
KNOWN_LIST_FIELDS = {"ips", "macs"}

# Reserved field that contains the properties array
PROPERTIES_FIELD = "properties"


def format_list_value(values: Any, max_items: int = MAX_LIST_ITEMS) -> str:
    """Format list values as comma-separated string."""
    if not isinstance(values, list):
        return str(values) if values is not None else ""
    return ", ".join(str(v) for v in values[:max_items] if v is not None)


def _clean_property_name(name: str) -> str:
    name = str(name).strip().lower()
    name = name.replace(' ', '_').replace('-', '_')
    name = ''.join(c if (c.isalnum() or c == '_') else '' for c in name)
    while '__' in name:
        name = name.replace('__', '_')
    return name.strip('_')


def extract_properties(properties: List[Dict[str, Any]], prefix: str = PREFIX) -> Dict[str, str]:
    """Extract and flatten properties into a namespaced dict."""
    result: Dict[str, str] = {}
    if not isinstance(properties, list):
        return result
    for prop in properties:
        if not isinstance(prop, dict):
            continue
        name = str(prop.get("name", "")).strip()
        value = prop.get("value")
        if not name or value is None or not str(value).strip():
            continue
        clean_name = _clean_property_name(name)
        if clean_name:
            key = f"{prefix}prop_{clean_name}"
            result[key] = str(value)
    return result


def compact_asset(asset: Optional[Dict[str, Any]], prefix: str = PREFIX) -> Dict[str, str]:
    """Convert asset data to a compact enrichment dict."""
    if not asset:
        return {}
    enrichment: Dict[str, str] = {}
    for field_name, field_value in asset.items():
        if field_name == PROPERTIES_FIELD:
            if isinstance(field_value, list):
                enrichment.update(extract_properties(field_value, prefix))
            continue
        if field_value is None:
            continue
        if field_name in KNOWN_LIST_FIELDS or isinstance(field_value, list):
            formatted_value = format_list_value(field_value)
            if formatted_value:
                enrichment[f"{prefix}{field_name}"] = formatted_value
        else:
            enrichment[f"{prefix}{field_name}"] = str(field_value)
    return enrichment


def process_entity(entity, api_manager, logger) -> Dict[str, Any]:
    """Process a single entity for enrichment."""
    identifier = entity.identifier

    if entity.entity_type != EntityTypes.ADDRESS:
        return {"error": "Unsupported entity type (expected IP address)"}

    if not validate_ip_address(identifier):
        return {"error": "Invalid IPv4 address format"}

    try:
        asset = api_manager.get_asset_by_ip(identifier)
        if not asset:
            return {"error": "Asset not found"}

        enrichment = compact_asset(asset)
        entity.additional_properties.update(enrichment)
        entity.is_enriched = True

        logger.info(f"Successfully enriched entity: {identifier}")
        return enrichment

    except Exception as e:
        logger.error(f"Failed to enrich entity {identifier}: {e}")
        return {"error": str(e)}


def build_output_message(enriched_entities: List, failed_entities: List[str]) -> str:
    """Build the final output message."""
    messages: List[str] = []
    if enriched_entities:
        enriched_ids = [entity.identifier for entity in enriched_entities]
        enriched_joined = "\n".join(enriched_ids)
        messages.append(f"Successfully enriched:\n{enriched_joined}")
    else:
        messages.append("No assets were enriched.")
    if failed_entities:
        failed_joined = "\n".join(failed_entities)
        messages.append(f"Failed to enrich:\n{failed_joined}")
    return "\n\n".join(messages)


@output_handler
def main():
    """Enrich asset information for IP address entities."""
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - Enrich Asset Information"
    siemplify.LOGGER.info("================= Main - Started =================")

    try:
        # Initialize API manager
        api_root, api_key, verify_ssl = get_integration_params(siemplify)
        api_manager = ApiManager(api_root, api_key, verify_ssl, siemplify.LOGGER)

        enriched_entities = []
        failed_entities = []
        result_json = {}

        # Process each entity
        for entity in siemplify.target_entities:
            identifier = entity.identifier
            result = process_entity(entity, api_manager, siemplify.LOGGER)

            result_json[identifier] = result

            if "error" in result:
                failed_entities.append(identifier)
            else:
                enriched_entities.append(entity)

        # Update enriched entities
        if enriched_entities:
            try:
                siemplify.update_entities(enriched_entities)
            except Exception as e:
                siemplify.LOGGER.warning(f"Failed to update entities: {e}")

        # Determine final status
        success = bool(enriched_entities)
        status = EXECUTION_STATE_COMPLETED if success else EXECUTION_STATE_FAILED
        output_message = build_output_message(enriched_entities, failed_entities)

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to enrich assets in {INTEGRATION_NAME}: {e}")
        siemplify.LOGGER.exception(e)

        status = EXECUTION_STATE_FAILED
        output_message = f"{ERRORS['ACTION']['FAILED']} {e}"
        success = False
        result_json = {"error": str(e)}

    siemplify.LOGGER.info(f"Action completed - Status: {status}")
    siemplify.result.add_result_json(result_json)
    siemplify.end(output_message, success, status)


if __name__ == "__main__":
    main()
