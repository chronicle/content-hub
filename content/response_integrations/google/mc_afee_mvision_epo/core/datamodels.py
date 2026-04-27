from __future__ import annotations
from TIPCommon import add_prefix_to_dict


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Tag(BaseModel):
    def __init__(self, raw_data, tag_id):
        super(Tag, self).__init__(raw_data)
        self.tag_id = tag_id


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        group_name,
        host,
        ip,
        uuid,
        products_installed,
        device_id,
        lastcommunicated,
        managedState,
        osplatform,
        operatingsystem,
        windowsdomain,
        dnsname,
        datversion,
        username,
        groups,
        tags,
    ):
        super(Device, self).__init__(raw_data)
        self.group_name = group_name
        self.host = host
        self.ip = ip
        self.uuid = uuid
        self.products_installed = products_installed
        self.device_id = device_id
        self.lastcommunicated = lastcommunicated
        self.managedState = managedState
        self.osplatform = osplatform
        self.operatingsystem = operatingsystem
        self.windowsdomain = windowsdomain
        self.dnsname = dnsname
        self.datversion = datversion
        self.username = username
        self.groups = groups
        self.tags = tags

    def to_enrichment_data(self, prefix):
        return add_prefix_to_dict(
            {
                "id": self.device_id,
                "uuid": self.uuid,
                "lastcommunicated": self.lastcommunicated,
                "managedState": self.managedState,
                "ipaddress": self.ip,
                "osplatform": self.osplatform,
                "operatingsystem": self.operatingsystem,
                "hostname": self.host,
                "windowsdomain": self.windowsdomain,
                "dnsname": self.dnsname,
                "datversion": self.datversion,
                "username": self.username,
                "groups": self.groups,
                "tags": self.tags,
            },
            prefix,
        )


class ProductsInstalled(BaseModel):
    def __init__(self, raw_data, product, version):
        super(ProductsInstalled, self).__init__(raw_data)
        self.product = product
        self.version = version

    def to_table_data(self):
        return {"Product Name": self.product, "Version": self.version}


class Group(BaseModel):
    def __init__(self, raw_data, id, name, description):
        super(Group, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description

    def to_table(self):
        return {"ID": self.id, "Name ": self.name, "Description ": self.description}


class Endpoint(BaseModel):
    def __init__(self, raw_data, uuid, ipaddress, hostname, username):
        super(Endpoint, self).__init__(raw_data)
        self.uuid = uuid
        self.ipaddress = ipaddress
        self.hostname = hostname
        self.username = username

    def to_table(self):
        return {
            "UUID ": self.uuid,
            "IP Address ": self.ipaddress,
            "Hostname  ": self.hostname,
            "Username ": self.username,
        }


class TagDetails(BaseModel):
    def __init__(self, raw_data, id, name, description):
        super(TagDetails, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description

    def to_table(self):
        return {"ID": self.id, "Name ": self.name, "Description ": self.description}
