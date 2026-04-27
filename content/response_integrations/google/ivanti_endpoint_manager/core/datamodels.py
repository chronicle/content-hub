from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict


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


class Query(BaseModel):
    def __init__(self, raw_data, name):
        super(Query, self).__init__(raw_data)
        self.name = name

    def to_json(self):
        return self.name


class DeliveryMethod(BaseModel):
    def __init__(self, raw_data, name, type, description):
        super(DeliveryMethod, self).__init__(raw_data)
        self.name = name
        self.type = type
        self.description = description

    def to_table(self):
        return {"Type": self.type, "Name": self.name, "Description": self.description}


class Field(BaseModel):
    def __init__(self, raw_data, name):
        super(Field, self).__init__(raw_data)
        self.name = name


class Machine(BaseModel):
    def __init__(
        self,
        raw_data,
        guid,
        device_name,
        domain_name,
        last_login,
        ip_address,
        subnet_mask,
        mac_address,
        os_name,
    ):
        super(Machine, self).__init__(raw_data)
        self.guid = guid
        self.device_name = device_name
        self.domain_name = domain_name
        self.last_login = last_login
        self.ip_address = ip_address
        self.subnet_mask = subnet_mask
        self.mac_address = mac_address
        self.os_name = os_name
        self.machine_details = None

    def to_json(self):
        if self.machine_details:
            self.raw_data["column_set_info"] = self.machine_details
        return self.raw_data

    def to_insight(self):
        return (
            f"<br><p>"
            f"<strong>IP: </strong>{self.ip_address or 'N/A'}"
            f"<strong><br />Mac Address: </strong>{self.mac_address or 'N/A'}"
            f"<strong><br />Hostname: </strong>{self.device_name or 'N/A'}<br />"
            f"<strong>OS: </strong>{self.os_name or 'N/A'}<br />"
            f"<strong>Last Login: </strong>{self.last_login or 'N/A'}"
            f"</p>"
        )


class Vulnerability(BaseModel):
    def __init__(self, raw_data, severity_code):
        super(Vulnerability, self).__init__(raw_data)
        self.severity_code = severity_code


class Package(BaseModel):
    def __init__(self, raw_data, type, name, description, primary_file):
        super(Package, self).__init__(raw_data)
        self.type = type
        self.name = name
        self.description = description
        self.primary_file = primary_file

    def to_table(self):
        return {
            "Type": self.type,
            "Name": self.name,
            "Description": self.description,
            "Primary File": self.primary_file,
        }


class ColumnSet(BaseModel):
    def __init__(self, raw_data, name):
        super(ColumnSet, self).__init__(raw_data)
        self.name = name


class QueryResult(BaseModel):
    def __init__(self, raw_data, device_name, type, os_name):
        super(QueryResult, self).__init__(raw_data)
        self.device_name = device_name
        self.type = type
        self.os_name = os_name

    def to_json(self):
        return {
            "Device_x0020_Name": self.device_name,
            "Type": self.type,
            "OS_x0020_Name": self.os_name,
        }


class TaskResult(BaseModel):
    def __init__(self, raw_data, machine_data):
        super(TaskResult, self).__init__(raw_data)
        self.machine_data = machine_data


class TaskMachine(BaseModel):
    def __init__(self, raw_data, guid, name, status):
        super(TaskMachine, self).__init__(raw_data)
        self.guid = guid
        self.name = name
        self.status = status
