from __future__ import annotations
from TIPCommon import dict_to_flat


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


class SearchStatus(BaseModel):
    def __init__(self, raw_data, name, run_by, job_end_time, status):
        super(SearchStatus, self).__init__(raw_data)
        self.name = name
        self.run_by = run_by
        self.job_end_time = job_end_time
        self.status = status

    def to_json(self):
        return {
            "Name": self.name,
            "RunBy": self.run_by,
            "JobEndTime": self.job_end_time,
            "Status": self.status,
        }


class SearchResult(BaseModel):
    def __init__(
        self, raw_data, location, sender, subject, type, size, received_time, data_link
    ):
        super(SearchResult, self).__init__(raw_data)
        self.location = location
        self.sender = sender
        self.subject = subject
        self.type = type
        self.size = size
        self.received_time = received_time
        self.data_link = data_link

    def to_table(self):
        return dict_to_flat(
            {
                "Received Time": self.received_time,
                "Sender": self.sender,
                "Recipient": self.location,
                "Subject": self.subject,
            }
        )

    def to_raw_data(self):
        return self.raw_data


class Rule(BaseModel):
    def __init__(self, raw_data, name, items):
        super(Rule, self).__init__(raw_data)
        self.name = name
        self.items = items

    def to_json(self):
        return {
            "Priority": self.raw_data.get("Priority"),
            "ManuallyModified": self.raw_data.get("ManuallyModified"),
            "Description": self.raw_data.get("Description"),
            "Conditions": self.raw_data.get("Conditions"),
            "Actions": self.raw_data.get("Actions"),
            "State": self.raw_data.get("State"),
            "Mode": self.raw_data.get("Mode"),
            "FromAddressContainsWords": self.raw_data.get("FromAddressContainsWords"),
            "Identity": self.raw_data.get("Identity"),
            "Name": self.raw_data.get("Name"),
            "DistinguishedName": self.raw_data.get("DistinguishedName"),
            "IsValid": self.raw_data.get("IsValid"),
            "From": self.raw_data.get("From"),
            "Guid": self.raw_data.get("Guid"),
            "ImmutableId": self.raw_data.get("ImmutableId"),
            "WhenChanged": self.raw_data.get("WhenChanged"),
            "ExchangeVersion": self.raw_data.get("ExchangeVersion"),
            "OrganizationId": self.raw_data.get("OrganizationId"),
            "ObjectState": self.raw_data.get("ObjectState"),
        }

    def to_table(self):
        return [{"Items": item} for item in self.items]
