from __future__ import annotations
import urllib.parse
import uuid

from soar_sdk.SiemplifyDataModel import EntityTypes

from TIPCommon.extraction import extract_configuration_param
from .adapter import create_drp_poller

# Import Managers
from .config import Config


def extract_host(value, fallback=""):
    """Return a display-friendly host from a URL-ish string.

    Used by the DRP connectors to build human-readable case/alert names of the
    form "<prefix>: <host>" so analysts can distinguish cases in the queue.

    - Handles http/https URLs via urllib.parse.urlsplit (uses netloc).
    - Handles schemeless 'host/path' input by taking the first path segment.
    - Strips userinfo ('user:pass@'), port (':8080'), and a leading 'www.'.
    - Lowercases the result.
    - If nothing parseable is found, returns `fallback` when given, otherwise
      a safe truncated copy of the original value (max 60 chars).
    """
    if not value:
        return fallback or ""

    raw = str(value).strip()
    if not raw:
        return fallback or ""

    try:
        parts = urllib.parse.urlsplit(raw)
        host = parts.netloc
        if not host:
            # Schemeless input like 'example.com/path' — urlsplit puts the
            # whole thing into .path. Take the first path segment as host.
            host = raw.split("?", 1)[0].split("#", 1)[0].split("/", 1)[0]

        # Drop userinfo and port, if present.
        if "@" in host:
            host = host.rsplit("@", 1)[-1]
        if ":" in host:
            host = host.split(":", 1)[0]

        host = host.strip().lower()
        if host.startswith("www."):
            host = host[4:]

        if host:
            return host
    except Exception:
        pass

    if fallback:
        return fallback
    return raw[:60]


class EntityValidator(object):

    def __init__(self):
        pass

    def get_entity_type(self, entity):
        import validators

        entity = entity.lower()

        if validators.domain(entity):
            return entity, "domain"

        elif validators.ipv4(entity):
            return entity, "ip"

        elif validators.sha256(entity) or validators.sha1(entity) or validators.md5(entity):
            return entity, "hash"

        elif validators.url(entity):

            _address = urllib.parse.urlsplit(entity).netloc

            if validators.domain(_address):
                return _address, "domain"

            elif validators.ipv4(_address):
                return _address, "ip"

        elif validators.email(entity):
            return entity, "email"

        elif validators.card_number(entity):
            return entity, "cardInfo.number"

        else:
            return None, None


class GIBConnector:

    def __init__(self, siemplify):
        self.siemplify = siemplify

    def init_action_poller(self, creds=None):
        self.siemplify.LOGGER.info("Provider Name = " + Config.PROVIDER_NAME)
        self.siemplify.LOGGER.info('──── GET USER PARAMS')

        if creds:
            username, api_key, api_url = creds
        else:
            username = extract_configuration_param(self.siemplify, provider_name=Config.PROVIDER_NAME, param_name="API login", print_value=True)
            api_key = extract_configuration_param(self.siemplify, provider_name=Config.PROVIDER_NAME, param_name="API key", print_value=False)
            api_url = extract_configuration_param(self.siemplify, provider_name=Config.PROVIDER_NAME, param_name="API URL", print_value=True)

        if api_url and not api_url.endswith("/"):
            api_url += "/"

        self.siemplify.LOGGER.info('──── API INITIALIZATION')
        poller = create_drp_poller(username=username, api_key=api_key, api_url=api_url)
        return poller


class CaseProcessor:

    entity_types = {
        0: "SourceHostName",
        1: "SourceAddress",
        2: "SourceUserName",
        3: "SourceProcessName",
        4: "SourceMacAddress",
        5: "DestinationHostName",
        6: "DestinationAddress",
        7: "DestinationUserName",
        8: "DestinationProcessName",
        9: "DestinationMacAddress",
        "URL": "DestinationURL",            # 10
        11: "Process",
        12: "FileName",
        13: "FileHash",
        14: "EmailSubject",
        15: "ThreatSignature",
        16: "USB",
        17: "Deployment",
        18: "CreditCard",
        19: "PhoneNumber",
        20: "CVE",
        21: "ThreatActor",
        22: "ThreatCampaign",
        23: "GenericEntity",
        24: "ParentProcess",
        25: "ParentHash",
        26: "ChildProcess",
        27: "ChildHash",
        28: "SourceDomain",
        "DOMAIN": "DestinationDomain",      # 29
        30: "IPSet"
    }

    def __init__(self, siemplify):
        self.siemplify = siemplify

    def add_to_case(self, case_id, alert_id, entity, entity_type="URL", property_value="value2"):

        case_id = str(case_id)
        entity = str(entity)
        entity_type = self.entity_types.get(entity_type)

        if alert_id is None:
            alert_id = str(uuid.uuid4())

        # Property value - is Group-IB feed ID to use it in Approve or Reject actions
        properties = {"property": property_value}

        self.siemplify.add_entity_to_case(
            # Case ID to apply
            case_id=case_id,
            # Entity
            entity_identifier=entity,
            entity_type=entity_type,
            # Params
            is_internal=True,
            is_suspicous=True,
            is_enriched=False,
            is_vulnerable=False,
            properties=properties,
            # Group-IB ID
            alert_identifier=alert_id,
            # Environment
            environment=None
        )
