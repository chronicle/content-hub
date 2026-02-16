from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.NSMManager import NsmManager

# Consts
# Provider Sign.
ACTION_SCRIPT_NAME = "Quarantine IP"
NSM_PROVIDER = "McAfeeNSM"

# Entity type consts.
ADDRESS = EntityTypes.ADDRESS

# Map duration times(Right now action supports only 'until_release').
DURATIONS_MAP = {
    "15m": "FIFTEEN_MINUTES",
    "30m": "THIRTY_MINUTES",
    "45m": "FORTYFIVE_MINUTES",
    "1h": "SIXTY_MINUTES",
    "4h": "FOUR_HOURS",
    "8h": "EIGHT_HOURS",
    "12h": "TWELVE_HOURS",
    "16h": "SIXTEEN_HOURS",
    "until_released": "UNTIL_EXPLICITLY_RELEASED",
}


@output_handler
def main():
    # Configuration
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_SCRIPT_NAME
    # Define script name

    conf = siemplify.get_configuration(NSM_PROVIDER)
    nsm_manager = NsmManager(
        conf["API Root"],
        conf["Username"],
        conf["Password"],
        conf["Domain ID"],
        conf["Siemplify Policy Name"],
        conf["Sensors Names List Comma Separated"],
    )
    # Define Variables
    quarantined_identifiers = []
    result_value = False

    # Extract duration format for API POST request from DURATIONS_MAP dict.
    duration_format = DURATIONS_MAP["until_released"]
    sensors_names_list_string = conf["Sensors Names List Comma Separated"]

    # Split the string list into list of strings.
    sensors_names_list = sensors_names_list_string.split(",")

    for entity in siemplify.target_entities:
        if entity.entity_type == ADDRESS:
            # Quarantine address in each sensor.
            for sensor_name in sensors_names_list:
                # Extract sensor id from SENSORS_NAMES_TO_IDS dict -> Sensors are 
                # inserted dynamicaly by the user and cannot be stored in a Const.
                try:
                    sensor_id = nsm_manager.get_sensor_id_by_name(sensor_name)
                    res = nsm_manager.quarantine_ip(
                        sensor_id, entity.identifier, duration_format
                    )
                    # Verify that the address blocked at least in one sensor.s
                    if res and entity.identifier not in quarantined_identifiers:
                        # If address was quarantined append it's identifier to 
                        # 'quarantined_identifiers' list.
                        quarantined_identifiers.append(entity.identifier)
                except Exception as err:
                    siemplify.LOGGER.error(
                        f"Error quarantine IP {entity.identifier}"
                        f" for sensor {sensor_name}, ERROR: {err}"
                    )
                    siemplify.LOGGER._log.exception(err)

    # End session with NSM.
    nsm_manager.logout()

    # Organize output message.
    if quarantined_identifiers:
        output_message = f"Successfully quarantined {','.join(quarantined_identifiers)}"
        result_value = True
    else:
        output_message = "No address was quarantined."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
