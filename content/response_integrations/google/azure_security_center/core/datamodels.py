from __future__ import annotations
import copy
import uuid

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.transformation import dict_to_flat
from . import consts
from .utils import convert_string_to_unix_time, trim_keys_spaces


class RegulatoryStandard:
    """
    Regulatory Standard data model.
    """

    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        type=None,
        state=None,
        passedControls=None,
        skippedControls=None,
        failedControls=None,
        unsupportedControls=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.name = name
        self.type = type
        self.state = state
        self.passed_controls = passedControls
        self.skipped_controls = skippedControls
        self.failed_controls = failedControls
        self.unsupported_controls = unsupportedControls

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return {
            "Name": self.name if self.name else "",
            "State": self.state if self.state else "",
            "Passed Controls": (
                self.passed_controls if self.passed_controls is not None else ""
            ),
            "Failed Controls": (
                self.failed_controls if self.failed_controls is not None else ""
            ),
            "Skipped Controls": (
                self.skipped_controls if self.skipped_controls is not None else ""
            ),
            "Unsupported Controls": (
                self.unsupported_controls
                if self.unsupported_controls is not None
                else ""
            ),
        }


class RegulatoryControl:
    """
    Regulatory Control data model.
    """

    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        type=None,
        standard_name=None,
        state=None,
        description=None,
        passedAssessments=None,
        failedAssessments=None,
        skippedAssessments=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.name = name
        self.type = type
        self.standard_name = standard_name
        self.description = description
        self.state = state
        self.passed_assessments = passedAssessments
        self.failed_assessments = failedAssessments
        self.skipped_assessment = skippedAssessments

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return {
            "Name": self.name if self.name else "",
            "Description": self.description if self.description else "",
            "State": self.state if self.state else "",
            "Passed Assessments": (
                self.passed_assessments if self.passed_assessments is not None else ""
            ),
            "Failed Assessments": (
                self.failed_assessments if self.failed_assessments is not None else ""
            ),
            "Skipped Assessments": (
                self.skipped_assessment if self.skipped_assessment is not None else ""
            ),
        }


class GraphAlert:
    """
    Alert data model in Microsoft Graph
    """

    def __init__(
        self,
        raw_data,
        id=None,
        location=None,
        createdDateTime=None,
        category=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.location = location
        self.id = id
        self.create_time = createdDateTime
        self.category = category

        try:
            self.create_time_ms = convert_string_to_unix_time(self.create_time)
        except Exception:
            self.create_time_ms = 1


class AzureAlert:
    """
    Alert data model in Azure Security Center
    """

    def __init__(
        self,
        raw_data,
        type=None,
        name=None,
        entities_obj=None,
        is_incident=None,
        timeGeneratedUtc=None,
        processingEndTimeUtc=None,
        startTimeUtc=None,
        endTimeUtc=None,
        severity=None,
        alert_type=None,
        description=None,
        alert_display_name=None,
        alert_id=None,
        alert_location=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.entities_obj = (
            entities_obj or []
        )  # list of alert's entities datamodels {[datamodels.AzureEntity]}
        self.is_incident = is_incident
        self.type = type
        self.name = name
        self.severity = severity
        self.time_generated_utc = timeGeneratedUtc
        self.processing_end_time_utc = processingEndTimeUtc
        self.start_time_utc = startTimeUtc
        self.end_time_utc = endTimeUtc
        self.alert_type = alert_type
        self.description = description
        self.alert_display_name = alert_display_name
        self.alert_location = alert_location
        self.alert_id = alert_id

        try:
            self.processing_end_time_utc_ms = convert_string_to_unix_time(
                self.processing_end_time_utc if self.processing_end_time_utc else ""
            )
        except Exception:
            self.processing_end_time_utc_ms = 1

        try:
            self.time_generated_utc_ms = convert_string_to_unix_time(
                self.time_generated_utc if self.time_generated_utc else ""
            )
        except Exception:
            self.time_generated_utc_ms = 1

        try:
            self.start_time_utc_ms = convert_string_to_unix_time(
                self.start_time_utc if self.start_time_utc else ""
            )
        except Exception:
            self.start_time_utc_ms = 1

        try:
            self.end_time_utc_ms = convert_string_to_unix_time(
                self.end_time_utc if self.end_time_utc else ""
            )
        except Exception:
            self.end_time_utc_ms = 1

    @property
    def siemplify_severity(self):
        return consts.SIEMPLIFY_SEVERITIES.get(
            str(self.severity).lower() if self.severity else "info", -1
        )

    def as_alert_info(self, environment_common, events=None):
        """
        Create an AlertInfo out of the current finding
        :param environment_common: {EnvironmentHandle} The environment common object for fetching the environment
        :param events: {[dict]} list of flatted dictionary that will be assigned as events for the alert
        :return: {AlertInfo} The created AlertInfo object
        """
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = str(uuid.uuid4())
        alert_info.display_id = str(uuid.uuid4())

        alert_info.name = self.alert_display_name
        alert_info.description = self.description
        alert_info.device_vendor = consts.VENDOR
        alert_info.device_product = consts.PRODUCT

        alert_info.priority = self.siemplify_severity
        alert_info.rule_generator = self.alert_type

        alert_info.start_time = self.start_time_utc_ms
        alert_info.end_time = self.end_time_utc_ms
        # Some event keys contain spaces from the raw API response. To ensure proper event field mappings, we trim the spaces.
        alert_info.events = (
            [trim_keys_spaces(event) for event in events] if events else []
        )
        return alert_info

    def mapped_times_raw_data(self):
        raw_data = copy.deepcopy(self.raw_data)
        # Convert times to timestamps
        raw_data["properties"]["timeGeneratedUtc"] = (
            self.time_generated_utc_ms
            if self.time_generated_utc_ms != 1
            else self.time_generated_utc
        )
        raw_data["properties"]["processingEndTimeUtc"] = (
            self.processing_end_time_utc_ms
            if self.processing_end_time_utc_ms != 1
            else self.processing_end_time_utc
        )
        raw_data["properties"]["startTimeUtc"] = (
            self.start_time_utc_ms
            if self.start_time_utc_ms != 1
            else self.start_time_utc
        )
        raw_data["properties"]["endTimeUtc"] = (
            self.end_time_utc_ms if self.end_time_utc_ms != 1 else self.end_time_utc
        )
        return raw_data

    def to_events(self, event_location=True):
        """
        Non incident alert events.
        :param event_location: {str} True if events should have 'location':<alert location> key,value elements in event data. False
        otherwise
        :return: {[str]} list of non incident alert events
        """
        event_results = []
        for event in self.entities_obj:
            event_data = self.mapped_times_raw_data()
            if event_location:
                event_data.get("properties", {})["location"] = self.alert_location
            event_data.get("properties", {})["entities"] = event.as_event()
            event_results.append(dict_to_flat(event_data))

        return event_results


class AzureEntity:
    """
    Entity data model for an alert in Azure Security Center
    """

    def __init__(
        self,
        raw_data,
        id=None,
        displayName=None,
        compromisedEntity=None,
        count=None,
        severity=None,
        alertType=None,
        vendorName=None,
        providerName=None,
        startTimeUtc=None,
        endTimeUtc=None,
        Location=None,
        system_alert_ids=None,
    ):
        self.raw_data = raw_data
        self.id = id
        self.display_name = displayName
        self.compromised_entity = compromisedEntity
        self.count = count
        self.severity = severity
        self.alert_type = alertType
        self.provider_name = providerName
        self.vendor_name = vendorName
        self.start_time = startTimeUtc
        self.end_time = endTimeUtc
        self.location = Location
        self.system_alert_ids = system_alert_ids or []

        try:
            self.start_time_utc_ms = convert_string_to_unix_time(
                self.start_time if self.start_time else ""
            )
        except Exception:
            self.start_time_utc_ms = 1

        try:
            self.end_time_utc_ms = convert_string_to_unix_time(
                self.end_time if self.end_time else ""
            )
        except Exception:
            self.end_time_utc_ms = 1

    def as_event(self):
        data = copy.deepcopy(self.raw_data)
        # Convert times to timestamps
        if self.start_time and self.start_time != 1:
            data["startTimeUtc"] = self.start_time_utc_ms
        if self.end_time and self.end_time != 1:
            data["endTimeUtc"] = self.start_time_utc_ms
        return dict_to_flat(data)


class AzureIncidentAlert(AzureAlert):
    """
    Incident alert data model in Azure Security Center
    """

    def __init__(self, **kwargs):
        super(AzureIncidentAlert, self).__init__(**kwargs)

    def to_events(self, entity_incident: AzureEntity, entity_alert: AzureAlert):
        """
        Returns list of events for system alert id of an incident alert
        :param: {datamodels.AzureEntity} Incident Azure alert entity data model
        :param: {datamodels.AzureAlert} Non incident Azure alert
        :return: {[str]} list of non incident alert events
        """
        entity_incident_events = entity_alert.to_events(event_location=False)
        event_results = []

        for event in entity_incident_events:
            event_data = self.mapped_times_raw_data()
            event_data.get("properties", {})["entities"] = {}
            event_data.get("properties", {})["entities"] = entity_incident.as_event()
            event_data.get("properties", {})["entities"]["alertInfo"] = event
            event_results.append(dict_to_flat(event_data))

        return event_results
