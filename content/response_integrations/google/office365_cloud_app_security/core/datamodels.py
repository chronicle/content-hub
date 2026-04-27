from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
from enum import Enum


class CloudAppPriorityEnum(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


class SiemplifyPriorityEnum(Enum):
    INFO = -1
    LOW = 40
    MEDIUM = 60
    HIGH = 80
    CRITICAL = 100


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Alert:
    def __init__(
        self,
        raw_data,
        alert_id=None,
        start_time=None,
        end_time=None,
        alert_name=None,
        alert_severity=None,
        product_name=None,
        vendor_name=None,
        rule_generator=None,
        description=None,
    ):
        self.raw_data = raw_data
        self.alert_id = alert_id
        self.start_time = start_time
        self.end_time = end_time
        self.alert_name = alert_name
        self.alert_severity = alert_severity
        self.vendor_name = vendor_name
        self.product_name = product_name
        self.rule_generator = rule_generator
        self.description = description

    BLACKLISTED_KEYS = ["entities"]

    def as_extension(self):
        return dict_to_flat(
            {k: v for k, v in self.raw_data.items() if k not in self.BLACKLISTED_KEYS}
        )


class Activity:
    def __init__(
        self,
        raw_data,
        description=None,
        user=None,
        ip_address=None,
        location=None,
        device=None,
        date=None,
    ):
        self.raw_data = raw_data
        self.description = description
        self.user = user
        self.ip_address = ip_address
        self.location = location
        self.device = device
        self.date = date

    def as_event(self):
        return dict_to_flat(self.raw_data)

    def to_enrichment_data(self):
        return {
            "MCAS_Activity": self.description,
            "MCAS_User": self.user,
            "MCAS_IP Address": self.ip_address,
            "MCAS_Location": self.location,
            "MCAS_Device": self.device,
            "MCAS_Date": self.date,
        }

    def to_json(self):
        return self.raw_data

    def to_table_data(self):
        return {
            "Activity": self.description,
            "User": self.user,
            "IP Address": self.ip_address,
            "Location": self.location,
            "Device": self.device,
            "Date": self.date,
        }


class Entity:
    def __init__(
        self,
        raw_data,
        is_admin=None,
        is_external=None,
        role=None,
        email=None,
        domain=None,
        threat_score=None,
        is_fake=None,
    ):
        self.raw_data = raw_data
        self.is_admin = is_admin
        self.is_external = is_external
        self.role = role
        self.email = email
        self.domain = domain
        self.threat_score = threat_score
        self.is_fake = is_fake

    def to_enrichment_data(self):
        return {
            "MCAS_is_admin": self.is_admin,
            "MCAS_is_external": self.is_external,
            "MCAS_role": self.role,
            "MCAS_email": self.email,
            "MCAS_domain": self.domain,
            "MCAS_threat_score": self.threat_score,
            "MCAS_is_fake": self.is_fake,
        }

    def to_json(self):
        return self.raw_data

    def to_table_data(self):
        return {
            "Is Admin": self.is_admin,
            "Is External": self.is_external,
            "Role": self.role,
            "Email": self.email,
            "Domain": self.domain,
            "Threat Score": self.threat_score,
            "Is Fake": self.is_fake,
        }


class File:
    def __init__(
        self,
        raw_data,
        name=None,
        owner_name=None,
        owner_address=None,
        alternate_link=None,
        app_name=None,
        is_folder=None,
        created_date=None,
        modified_date=None,
    ):
        self.raw_data = raw_data
        self.name = name
        self.owner_name = owner_name
        self.owner_address = owner_address
        self.alternate_link = alternate_link
        self.app_name = app_name
        self.is_folder = is_folder
        self.created_date = created_date
        self.modified_date = modified_date

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return {
            "Name": self.name,
            "Owner Name": self.owner_name,
            "Owner Email": self.owner_address,
            "Link": self.alternate_link,
            "App": self.app_name,
            "Folder": self.is_folder,
            "Creation Time": self.created_date,
            "Modification Time": self.modified_date,
        }


class IpAddressRange(BaseModel):
    def __init__(self, raw_data, id, name, subnets, category, organization, tags):
        super().__init__(raw_data)
        self.id = id
        self.name = name
        self.subnets = subnets
        self.category = category
        self.organization = organization
        self.tags = tags
