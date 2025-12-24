from __future__ import annotations

import urllib.parse
import uuid

import validators
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_configuration_param

from .adapter import PlaybookAdapter
from .config import Config
from .mapping import mapping_config


class EntityValidator(object):
    def __init__(self):
        pass

    def get_entity_type(self, entity):
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

    def entity_processor(self):
        ev = EntityValidator()

        # self.siemplify.LOGGER.info(self.siemplify.get_configuration(Config.PROVIDER_NAME))
        self.siemplify.LOGGER.info(self.siemplify.target_entities)
        self.siemplify.LOGGER.info(EntityTypes.__dict__)
        self.siemplify.LOGGER.info(EntityTypes.ADDRESS)

        for entity in self.siemplify.target_entities:
            input_type = ev.get_entity_type(entity.identifier)
            self.siemplify.LOGGER.info("{}  {}".format(entity.identifier, input_type))
            self.siemplify.LOGGER.info("{}  {}".format(entity.identifier, entity.entity_type))

    def init_action_poller(self, creds=None):
        self.siemplify.LOGGER.info("Provider Name = " + Config.PROVIDER_NAME)

        self.siemplify.LOGGER.info("──── GET USER PARAMS")

        # # Get GIB credentials
        if creds:
            username = creds[0]
            api_key = creds[1]
            api_url = creds[2]
        else:
            username = extract_configuration_param(
                self.siemplify,
                provider_name=Config.PROVIDER_NAME,
                param_name="API login",
                print_value=True,
            )
            api_key = extract_configuration_param(
                self.siemplify,
                provider_name=Config.PROVIDER_NAME,
                param_name="API key",
                print_value=False,
            )
            api_url = extract_configuration_param(
                self.siemplify,
                provider_name=Config.PROVIDER_NAME,
                param_name="API URL",
                print_value=True,
            )

        # Init set up
        gib_creds = {"creds": {"api_key": api_key, "username": username}}

        self.siemplify.LOGGER.info("──── API INITIALIZATION")

        # Proxy initialization
        proxies = {}

        # Get list of available collections
        collections = [col for col in mapping_config]
        self.siemplify.LOGGER.info(collections)

        # Adapter API initialization
        gib_adapter = PlaybookAdapter(
            gib_creds_dict=gib_creds,
            proxies=proxies,
            config_obj=Config,
            collections=collections,
            mapping_config=mapping_config,
            api_url=api_url,
        )

        # Poller initialization
        poller = gib_adapter.get_poller_object()

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
        "URL": "DestinationURL",  # 10
        11: "Process",
        12: "FileName",
        "HASH": "FileHash",
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
        "DOMAIN": "DestinationDomain",  # 29
        30: "IPSet",
        "IP": "ADDRESS",
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
            environment=None,
        )
