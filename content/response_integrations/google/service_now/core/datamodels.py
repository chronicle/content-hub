from __future__ import annotations

from TIPCommon.transformation import dict_to_flat, flat_dict_to_csv

from .constants import CANCELED, CLOSED, RESOLVED, STATES


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def is_empty(self):
        return not bool(self.raw_data)

    def to_csv(self):
        return flat_dict_to_csv(dict_to_flat(self.raw_data))

    def is_empty(self):
        return not bool(self.raw_data)


class UploadFile(BaseModel):
    def __init__(self, raw_data):
        super(UploadFile, self).__init__(raw_data)


class CMDB_Record(BaseModel):
    def __init__(self, raw_data, sys_id=None, name=None):
        super(CMDB_Record, self).__init__(raw_data)
        self.sys_id = sys_id
        self.name = name

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())

    def to_table(self):
        table = {"Sys ID": self.sys_id, "Name": self.name}
        return table


class CMDB_Record_Detail(BaseModel):
    def __init__(self, raw_data, inbound_relations=None, outbound_relations=None):
        super(CMDB_Record_Detail, self).__init__(raw_data)
        self.outbound_relations = outbound_relations
        self.inbound_relations = inbound_relations

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())


class Outbound_Relation(BaseModel):
    def __init__(
        self,
        raw_data,
        outbound_sys_id=None,
        outbound_cmdb_type=None,
        outbound_target=None,
    ):
        super(Outbound_Relation, self).__init__(raw_data)
        self.outbound_sys_id = outbound_sys_id
        self.outbound_cmdb_type = outbound_cmdb_type
        self.outbound_target = outbound_target
        self.type = "outbound"

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())

    def to_table(self):
        table = {
            "Sys ID": self.outbound_sys_id,
            "Type": self.outbound_cmdb_type,
            "Target": self.outbound_target,
            "Relation": self.type,
        }
        return table


class Inbound_Relation(BaseModel):
    def __init__(self, raw_data, inbound_sys_id=None, inbound_cmdb_type=None, inbound_target=None):
        super(Inbound_Relation, self).__init__(raw_data)
        self.inbound_sys_id = inbound_sys_id
        self.inbound_cmdb_type = inbound_cmdb_type
        self.inbound_target = inbound_target
        self.type = "inbound"

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())

    def to_table(self):
        table = {
            "Sys ID": self.inbound_sys_id,
            "Type": self.inbound_target,
            "Target": self.inbound_target,
            "Relation": self.type,
        }
        return table


class Attachment(BaseModel):
    def __init__(self, raw_data, download_link, download_path, filename, sys_id):
        super(Attachment, self).__init__(raw_data)
        self.sys_id = sys_id
        self.download_link = download_link
        self.download_path = download_path
        self.filename = filename

    def to_json(self):
        self.raw_data.update({"absolute_file_path": f"{self.download_path}/{self.filename}"})

        return self.raw_data


class User(BaseModel):
    def __init__(self, raw_data, sys_id, user_name, name, email):
        super(User, self).__init__(raw_data)
        self.sys_id = sys_id
        self.username = user_name
        self.name = name
        self.email = email

    def to_table(self):
        return {
            "Sys ID": self.sys_id,
            "Name": self.name,
            "Username": self.username,
            "Email": self.email,
        }

    def __hash__(self):
        return hash(f"{self.sys_id}_{self.username}_{self.email}")

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.sys_id == other.sys_id
            and self.email == other.email
            and self.username == self.username
        )

    def __ne__(self, other):
        return not self == other


class UserRelatedRecord(BaseModel):
    def __init__(self, raw_data, sys_id, short_description, created_at):
        super(UserRelatedRecord, self).__init__(raw_data)
        self.sys_id = sys_id
        self.short_description = short_description
        self.created_at = created_at

    def to_table(self):
        return {
            "Sys ID": self.sys_id,
            "Title": self.short_description,
            "Created At": self.created_at,
        }


class Incident(BaseModel):
    def __init__(
        self,
        raw_data,
        child_incidents=None,
        sys_id=None,
        caller_id=None,
        opener_id=None,
        sys_created_on=None,
        number=None,
        state=None,
        closed_at=None,
    ):
        super(Incident, self).__init__(raw_data)
        self.child_incidents = child_incidents
        self.sys_id = sys_id
        self.number = number
        self.state = state
        self.closed_at = closed_at
        self.caller_id = caller_id
        self.opener_id = opener_id
        self.sys_created_on = sys_created_on

    def __repr__(self):
        return f"Incident object {self.number}"

    def update_incident_with_user_info(self, user_info):
        self.raw_data.update(self._get_user_info(user_info))

    @staticmethod
    def _get_user_info(user_info):
        return {
            "caller_name": user_info.name,
            "caller_username": user_info.username,
            "caller_email_address": user_info.email,
            "opened_by_name": user_info.name,
            "opened_by_username": user_info.username,
            "opened_by_email_address": user_info.email,
        }


class ChildIncident(BaseModel):
    def __init__(self, raw_data, sys_id, number, short_description, created_at):
        super(ChildIncident, self).__init__(raw_data)
        self.sys_id = sys_id
        self.number = number
        self.short_description = short_description
        self.created_at = created_at

    def to_table(self):
        return {
            "Sys ID": self.sys_id,
            "Number": self.number,
            "Short Description": self.short_description,
            "Created At": self.created_at,
        }


class Comment(BaseModel):
    def __init__(self, raw_data, value, sys_created_on, element_id):
        super(Comment, self).__init__(raw_data)
        self.value = value
        self.sys_created_on = sys_created_on
        self.element_id = element_id


class ServiceNowObject(BaseModel):
    def __init__(self, raw_data, sys_id):
        super(ServiceNowObject, self).__init__(raw_data)
        self.sys_id = sys_id


class Ticket(BaseModel):
    def __init__(self, raw_data, state, sys_id, number):
        super(Ticket, self).__init__(raw_data)
        self.state = state
        self.sys_id = sys_id
        self.number = number

    def get_value(self, key):
        field = self.raw_data.get(key, "")
        if isinstance(field, str):
            return field.lower()
        return field.get("display_value", "").lower() or field.get("value", "").lower()

    @property
    def is_open(self):
        return self.state.lower() not in [
            RESOLVED,
            CLOSED,
            CANCELED,
            str(STATES[RESOLVED]),
            str(STATES[CLOSED]),
            str(STATES[CANCELED]),
        ]


class RecordDetail(BaseModel):
    def __init__(self, raw_data):
        super(RecordDetail, self).__init__(raw_data)


class AffectedCI(BaseModel):
    def __init__(self, raw_data: dict, sys_id: str, incident_sys_id: str):
        super().__init__(raw_data)
        self.sys_id = sys_id
        self.incident_sys_id = incident_sys_id


class AffectedCIDetails(BaseModel):
    def __init__(self, raw_data: dict, sys_id: str):
        super().__init__(raw_data)
        self.sys_id = sys_id
