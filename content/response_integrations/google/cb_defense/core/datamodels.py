from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
from copy import deepcopy

PREFIX = "CB_DEFENSE"


class Device:
    def __init__(
        self, raw_data, deviceId=None, name=None, policyName=None, status=None, **kwargs
    ):
        self.raw_data = raw_data
        self.device_id = deviceId
        self.name = name
        self.policy_name = policyName
        self.status = status

    def as_csv(self):
        return dict_to_flat(self.raw_data)

    def as_enrichment_data(self):
        return add_prefix_to_dict(dict_to_flat(self.raw_data), PREFIX)


class Event:
    def __init__(
        self,
        raw_data,
        eventId=None,
        eventType=None,
        shortDescription=None,
        createTime=None,
        alertScore=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.event_id = eventId
        self.event_type = eventType
        self.short_description = shortDescription
        self.create_time = createTime
        self.alert_score = alertScore

    def as_csv(self):
        temp = deepcopy(self.raw_data)
        temp.pop("deviceDetails", None)  # Not interesting
        temp.pop("netFlow", None)  # Complicated data - not very interesting

        return dict_to_flat(temp)


class Process:
    def __init__(
        self,
        raw_data,
        processId=None,
        numEvents=None,
        applicationPath=None,
        applicationName=None,
        sha256Hash=None,
        privatePid=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.process_id = processId
        self.num_events = numEvents
        self.application_path = applicationPath
        self.application_name = applicationName
        self.sha256 = sha256Hash
        self.private_pid = privatePid

    def as_csv(self):
        return dict_to_flat(self.raw_data)


class Policy:
    def __init__(
        self,
        raw_data,
        name=None,
        priorityLevel=None,
        id=None,
        description=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.name = name
        self.priority_level = priorityLevel
        self.id = id
        self.description = description
