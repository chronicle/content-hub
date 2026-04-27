from __future__ import annotations
from TIPCommon import write_content, IDS_DB_KEY, IDS_FILE_NAME
from .constants import SEVERITIES


def filter_processed_assets(logger, assets, assets_list, id_key="id"):
    """
    Filter assets that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param assets: {list} List of Asset objects
    :param assets_list: {list} List of assets to filter
    :param id_key: {str} The key of identifier
    :return: {list} List of filtered Alert objects
    """
    filtered_assets = []
    processed_ids = [
        item.get("asset_id") for item in assets_list if item.get("processed", False)
    ]

    for asset in assets:
        id = getattr(asset, id_key)

        if id not in processed_ids:
            filtered_assets.append(asset)
        else:
            logger.info(
                f"The asset {id} skipped since it has been already processed in this cycle"
            )

    return filtered_assets


def convert_list_to_comma_string(values_list):
    """
    Convert list to comma-separated string
    :param values_list: List of values
    :return: String with comma-separated values
    """
    return (
        ", ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )


def pass_severity_filter(siemplify, alert, lowest_severity):
    # severity filter
    if lowest_severity:
        filtered_severities = (
            SEVERITIES[SEVERITIES.index(lowest_severity.lower()) :]
            if lowest_severity.lower() in SEVERITIES
            else []
        )
        if not filtered_severities:
            siemplify.LOGGER.info(
                'Severity is not checked. Invalid value provided for "Lowest Severity To Fetch" '
                "parameter. Possible values are: {}.".format(
                    convert_list_to_comma_string(
                        [severity.title() for severity in SEVERITIES]
                    )
                )
            )
        if filtered_severities and alert.severity.lower() not in filtered_severities:
            siemplify.LOGGER.info(
                "Vulnerability {} with severity: {} did not pass filter. Lowest severity to fetch "
                "is {}.".format(alert.id, alert.severity, lowest_severity)
            )
            return False
    return True


def write_ids(siemplify, ids_json, ids_file_name=IDS_FILE_NAME, db_key=IDS_DB_KEY):
    """
    Write ids to the ids file
    :param siemplify: {Siemplify} Siemplify object.
    :param ids_json: {list} The ids to write to the file
    :param ids_file_name: {str} The name of the ids file.
    :param db_key: {str} the name of the key to be validated (in case the platform uses database)
    :return: {bool}
    """
    try:
        if all(item.get("processed", False) for item in ids_json):
            for asset_json in ids_json:
                asset_json["processed"] = False

        write_content(siemplify, ids_json, ids_file_name, db_key)
        return True
    except Exception as e:
        siemplify.LOGGER.error(f"Failed writing IDs to IDs file, ERROR: {e}")
        siemplify.LOGGER.exception(e)
        return False
