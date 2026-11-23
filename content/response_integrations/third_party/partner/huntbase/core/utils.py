from __future__ import annotations

import html
import ipaddress
import re
from typing import TYPE_CHECKING, Any

from TIPCommon.base.action.data_models import EntityTypesEnum
from TIPCommon.extraction import extract_configuration_param

from . import constants
from .huntbase_manager import HuntbaseManager

if TYPE_CHECKING:
    from collections.abc import Iterable


# SOAR entity type -> (lookup channel, Huntbase seed value type)
# "intel" values go to POST /intel/lookup, "entity" values to GET /entities/by-value.
ADDRESS = EntityTypesEnum.ADDRESS.value
DOMAIN = EntityTypesEnum.DOMAIN.value
URL = EntityTypesEnum.URL.value
FILEHASH = EntityTypesEnum.FILE_HASH.value
HOSTNAME = EntityTypesEnum.HOST_NAME.value
USER = EntityTypesEnum.USER.value

ENTITY_TYPE_MAP: dict[str, tuple[str, str]] = {
    ADDRESS: ("intel", "ip"),
    DOMAIN: ("intel", "domain"),
    URL: ("intel", "url"),
    FILEHASH: ("intel", "hash"),
    HOSTNAME: ("entity", "hostname"),
    USER: ("entity", "user"),
}
SUPPORTED_ENTITY_TYPES = tuple(ENTITY_TYPE_MAP)

# Huntbase seed value type -> entity_type for GET /entities/by-value
ENTITY_LOOKUP_TYPES = {"hostname": "device", "user": "user"}

_HASH_RE = re.compile(r"^(?:[A-Fa-f0-9]{32}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64})$")
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,63}$")

# Entity types whose values can go on a Huntbase watch list.
WATCHLIST_ENTITY_TYPES = (
    ADDRESS,
    DOMAIN,
    URL,
    FILEHASH,
)


def get_integration_params(siemplify: Any) -> tuple[str, str, bool]:  # noqa: ANN401
    api_root = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name=constants.PARAM_API_ROOT,
        default_value=constants.DEFAULT_API_ROOT,
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name=constants.PARAM_API_KEY,
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name=constants.PARAM_VERIFY_SSL,
        default_value=True,
        input_type=bool,
        print_value=True,
    )
    return api_root, api_key, verify_ssl


def create_manager(siemplify: Any, logger: Any = None) -> HuntbaseManager:  # noqa: ANN401
    api_root, api_key, verify_ssl = get_integration_params(siemplify)
    return HuntbaseManager(api_root=api_root, api_key=api_key, verify_ssl=verify_ssl, logger=logger)


def entity_value(entity: Any) -> str:  # noqa: ANN401
    """Return the entity's original identifier when SOAR kept one."""
    props = getattr(entity, "additional_properties", None) or {}
    return str(props.get("OriginalIdentifier") or entity.identifier).strip()


def entity_kind(entity: Any) -> tuple[str, str] | None:  # noqa: ANN401
    return ENTITY_TYPE_MAP.get(entity.entity_type)


def prefixed(properties: dict[str, Any]) -> dict[str, Any]:
    """Prefix enrichment keys with HB_ the way SOAR enrichment convention expects."""
    return {f"{constants.ENRICHMENT_PREFIX}_{key}": value for key, value in properties.items()}


def seed_values_from_entities(entities: Iterable[Any]) -> list[dict[str, str]]:  # noqa: ANN401
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


def external_ref(siemplify: Any, case_link: str | None = None, title: str | None = None) -> dict[str, Any] | None:  # noqa: ANN401
    """Reference to the SecOps case so the Huntbase item points back to it."""
    case_id = getattr(siemplify, "case_id", None)
    if not case_id:
        return None
    ref: dict[str, Any] = {"source": constants.EXTERNAL_REF_SOURCE, "id": str(case_id)}
    if case_link:
        ref["url"] = case_link
    if title:
        ref["title"] = title[:300]
    return ref


def is_http_url(value: str | None) -> bool:
    return bool(value) and re.match(r"^https?://[^\s/]+", value.strip(), re.IGNORECASE) is not None


def indicator_insight(value: str, details: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td><strong>{html.escape(str(key).replace('_', ' ').title())}</strong></td>"
        f"<td>{html.escape(str(val))}</td></tr>"
        for key, val in details.items()
        if key != "link"
    )
    link = details.get("link")
    link_html = f'<p><a href="{html.escape(link)}" target="_blank">Open in Huntbase</a></p>' if link else ""
    return f"<h3>Huntbase: {html.escape(value)}</h3><table>{rows}</table>{link_html}"
