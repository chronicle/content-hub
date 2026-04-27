from __future__ import annotations
from .datamodels import Device, Event, Process, Policy


class CBDefenseParser:
    """
    CB Defense Transformation Layer.
    """

    @staticmethod
    def build_siemplify_device_obj(device_data):
        return Device(raw_data=device_data, **device_data)

    @staticmethod
    def build_siemplify_event_obj(event_data):
        return Event(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_process_obj(process_data):
        return Process(raw_data=process_data, **process_data)

    @staticmethod
    def build_siemplify_policy_obj(policy_data):
        return Policy(raw_data=policy_data, **policy_data)
