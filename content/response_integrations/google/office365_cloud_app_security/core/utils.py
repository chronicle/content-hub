from __future__ import annotations
import datetime
from TIPCommon import dict_to_flat


def is_first_run(
    siemplify, offset_hours: int, connector_start_time: datetime.datetime
) -> bool:
    """
    Checks if first run of the connector.
    :param siemplify: {SiemplifyConnectorExecution} instance
    :param offset_hours: {int} Max hours backward connector parameter
    :param connector_start_time: {datetime.datetime} UTC now of connector run
    :return: True if connector's first run, otherwise False
    """
    last_run_timestamp = siemplify.fetch_timestamp(datetime_format=True)
    return (
        True
        if connector_start_time - last_run_timestamp
        > datetime.timedelta(hours=offset_hours)
        else False
    )


def get_alert_info_events(alert, activities):
    """
    Prepare AlertInfo events
    :param alert: {Alert} An alert instance
    :param activities: [list] A list of the Activity objects related to the alert
    :return: {list} The list of alert info events
    """
    events = [dict_to_flat(alert.raw_data)]

    for activity in activities:
        events.append(activity.as_event())

    return events


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def build_temporary_name(name):
    """
    Build temporary name from original name
    :param name: {str} original name
    :return: {str} temporary name
    """
    return f"{name}_testing_siemplify"


def find_ip_address_range_by_name(ip_address_ranges, name):
    """
    Find ip address range by name
    :param ip_address_ranges: {[IpAddressRange]} list of IpAddressRange objects
    :param name: {str} name of ip address range
    :return: {IpAddressRange} IpAddressRange object
    """
    return next(
        (
            ip_address_range
            for ip_address_range in ip_address_ranges
            if ip_address_range.name == name
        ),
        None,
    )
