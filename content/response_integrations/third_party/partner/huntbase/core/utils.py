from __future__ import annotations

import html
import ipaddress
import json
import re
from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import EntityTypesEnum
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.utils import get_entity_original_identifier

from . import constants
from .datamodels import HuntbaseConfig
from .huntbase_manager import HuntbaseManager

if TYPE_CHECKING:
    from collections.abc import Iterable

    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
    from TIPCommon.base.interfaces.logger import Logger
    from TIPCommon.types import ChronicleSOAR, SingleJson


# SOAR entity type -> (lookup channel, Huntbase seed value type)
# "intel" values go to POST /intel/lookup, "entity" values to GET /entities/by-value.
ADDRESS: str = EntityTypesEnum.ADDRESS.value
DOMAIN: str = EntityTypesEnum.DOMAIN.value
URL: str = EntityTypesEnum.URL.value
FILEHASH: str = EntityTypesEnum.FILE_HASH.value
HOSTNAME: str = EntityTypesEnum.HOST_NAME.value
USER: str = EntityTypesEnum.USER.value

ENTITY_TYPE_MAP: dict[str, tuple[str, str]] = {
    ADDRESS: ("intel", "ip"),
    DOMAIN: ("intel", "domain"),
    URL: ("intel", "url"),
    FILEHASH: ("intel", "hash"),
    HOSTNAME: ("entity", "hostname"),
    USER: ("entity", "user"),
}
SUPPORTED_ENTITY_TYPES: tuple[str, ...] = tuple(ENTITY_TYPE_MAP)

# Huntbase seed value type -> entity_type for GET /entities/by-value
ENTITY_LOOKUP_TYPES: dict[str, str] = {"hostname": "device", "user": "user"}

_HASH_RE: re.Pattern[str] = re.compile(r"^(?:[A-Fa-f0-9]{32}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64})$")
_DOMAIN_RE: re.Pattern[str] = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,63}$")
_HTTP_URL_RE: re.Pattern[str] = re.compile(r"^https?://[^\s/]+", re.IGNORECASE)

# Entity types whose values can go on a Huntbase watch list.
WATCHLIST_ENTITY_TYPES: tuple[str, ...] = (
    ADDRESS,
    DOMAIN,
    URL,
    FILEHASH,
)


def get_integration_params(siemplify: ChronicleSOAR) -> HuntbaseConfig:
    api_root: str = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name=constants.PARAM_API_ROOT,
        default_value=constants.DEFAULT_API_ROOT,
        is_mandatory=True,
        print_value=True,
    )
    api_key: str = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name=constants.PARAM_API_KEY,
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl: bool = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name=constants.PARAM_VERIFY_SSL,
        default_value=True,
        input_type=bool,
        print_value=True,
    )
    return HuntbaseConfig(api_root=api_root, api_key=api_key, verify_ssl=verify_ssl)


def create_manager(siemplify: ChronicleSOAR, logger: Logger | None = None) -> HuntbaseManager:
    return HuntbaseManager(get_integration_params(siemplify), logger=logger)


def entity_value(entity: DomainEntityInfo) -> str:
    """Return the entity's original identifier when SOAR kept one."""
    return str(get_entity_original_identifier(entity) or entity.identifier).strip()


def entity_kind(entity: DomainEntityInfo) -> tuple[str, str] | None:
    return ENTITY_TYPE_MAP.get(entity.entity_type)


def prefixed(properties: SingleJson) -> SingleJson:
    """Prefix enrichment keys with HB_ the way SOAR enrichment convention expects."""
    return {f"{constants.ENRICHMENT_PREFIX}_{key}": _property_value(value) for key, value in properties.items()}


def _property_value(value: object) -> str | int | float | bool:
    """Entity properties must be scalars: SecOps fails the whole entity update on an object or list."""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, default=str, sort_keys=True)


def seed_values_from_entities(entities: Iterable[DomainEntityInfo]) -> list[dict[str, str]]:
    seeds: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entity in entities:
        kind = entity_kind(entity)
        if kind is None:
            continue
        value = entity_value(entity)
        key = (kind[1], value.lower())
        if not value or key in seen:
            continue
        seen.add(key)
        seeds.append({"type": kind[1], "value": value})
    return seeds


def guess_value_type(value: str) -> str:
    """Best-effort Huntbase seed type for a free-text value."""
    text = value.strip()
    try:
        ipaddress.ip_address(text)
    except ValueError:
        pass
    else:
        return "ip"
    if _HASH_RE.match(text):
        return "hash"
    if "://" in text:
        return "url"
    if "@" in text:
        return "email"
    if _DOMAIN_RE.match(text):
        return "domain"
    return "hostname"


def external_ref(
    siemplify: ChronicleSOAR,
    case_link: str | None = None,
    title: str | None = None,
) -> SingleJson | None:
    """Reference to the SecOps case so the Huntbase item points back to it."""
    case_id: int | str | None = getattr(siemplify, "case_id", None)
    if not case_id:
        return None
    ref: SingleJson = {"source": constants.EXTERNAL_REF_SOURCE, "id": str(case_id)}
    if case_link:
        ref["url"] = case_link
    if title:
        ref["title"] = title[:300]
    return ref


def is_http_url(value: str | None) -> bool:
    return bool(value) and _HTTP_URL_RE.match(value.strip()) is not None


def indicator_insight(value: str, details: SingleJson) -> str:
    rows = "".join(
        f"<tr><td><strong>{html.escape(str(key).replace('_', ' ').title())}</strong></td>"
        f"<td>{html.escape(str(val))}</td></tr>"
        for key, val in details.items()
        if key != "link"
    )
    link = details.get("link")
    link_html = (
        f'<p><a href="{html.escape(link)}" target="_blank" rel="noopener noreferrer">Open in Huntbase</a></p>'
        if isinstance(link, str) and is_http_url(link)
        else ""
    )
    return f"<h3>Huntbase: {html.escape(value)}</h3><table>{rows}</table>{link_html}"
