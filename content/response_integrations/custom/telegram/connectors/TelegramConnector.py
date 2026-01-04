from __future__ import annotations

import sys

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import dict_to_flat, output_handler

from ..core.TelegramManager import TelegramManager
from ..core.Utils import LastMessage

# CONSTANTS
CONNECTOR_NAME = "Telegram Connector"
VENDOR = PRODUCT = "Telegram"
DEFAULT_PRIORITY = 60  # Default is Medium
RULE_GENERATOR_EXAMPLE = "Telegram"


def create_alert(siemplify, alert_id, created_event):
    """ """
    siemplify.LOGGER.info(f"----- Started processing Alert {alert_id}-----")
    alert_info = AlertInfo()

    # Initializes the alert_info Characteristics Fields
    alert_info.ticket_id = str(alert_id)
    alert_info.display_id = str(alert_id)
    alert_info.name = f"Telegram - {alert_id}"
    alert_info.rule_generator = RULE_GENERATOR_EXAMPLE
    alert_info.start_time = created_event["start_time"]
    alert_info.end_time = created_event["end_time"]
    # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
    alert_info.priority = DEFAULT_PRIORITY
    alert_info.device_vendor = VENDOR
    alert_info.device_product = PRODUCT
    try:
        if created_event is not None:
            alert_info.events.append(created_event)
        siemplify.LOGGER.info(f"Added Event {alert_id} to Alert {alert_id}")

    # Raise an exception if failed to process the event
    except Exception as e:
        siemplify.LOGGER.error(f"Failed to process event {alert_id}")
        siemplify.LOGGER.exception(e)

    return alert_info


def create_event_channel_message(siemplify, alert_id, last_message):
    """Returns the digested data of a single channel message"""
    siemplify.LOGGER.info(
        f"--- Started processing Event:  alert_id: {alert_id} | event_id: {alert_id}",
    )
    event = {}
    event = dict_to_flat(last_message)
    event["start_time"] = last_message["date"]
    event["end_time"] = last_message["date"]
    event["Name"] = "Telegram message - Channel message"
    event["device_product"] = (
        PRODUCT  # ie: describes the product the event originated from.
    )

    siemplify.LOGGER.info(
        f"--- Finished processing Event: alert_id: {alert_id} "
        "| event_name: Telegram message - channel message"
    )
    return event


def create_event_private_or_group_message(siemplify, alert_id, message):
    """Returns the digested data of a single private or group message"""
    siemplify.LOGGER.info(
        f"--- Started processing Event:  alert_id: {alert_id} | event_id: {alert_id}",
    )
    event = {}
    event = dict_to_flat(message)
    event["start_time"] = message["date"]
    event["end_time"] = message["date"]
    event["Name"] = "Telegram message - Private or group message"
    event["device_product"] = (
        PRODUCT  # ie: describes the product the event originated from.
    )

    siemplify.LOGGER.info(
        f"--- Finished processing Event: alert_id: {alert_id}"
        " | event_name: Telegram message - private or group message"
    )
    return event


@output_handler
def main(is_test_run):
    alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    # In case of running a test
    if is_test_run:
        siemplify.LOGGER.info("***** This is a test run ******")

    # Extracting the connector's params
    bot_api_token = siemplify.extract_connector_param(param_name="API Token")

    # Creating an instance of Telegram object
    all_messages_dict = {}
    try:
        telegram_manager = TelegramManager(bot_api_token)
        # Retrieve the last update id that was saved
        last_saved_update_id = LastMessage.get(siemplify=siemplify).id
        # The update id to start retrieve from
        if not is_test_run:
            start_update_id_to_retrieve = int(last_saved_update_id) + 1
        else:
            start_update_id_to_retrieve = 0

        # Get all the new messages from the last_saved_update_id+1
        # allowed_updates list will contain all the chats
        # you would like to retrieve data from.
        all_messages_dict = telegram_manager.get_updates(
            offset=start_update_id_to_retrieve,
            allowed_updates=[],
        )
        if all_messages_dict["result"]:  # Not empty
            for message in all_messages_dict["result"]:
                # Getting the unique id of each update message
                alert_id = message.get("update_id")
                created_event = None
                created_alert = None
                if "message" in message:  # If the update is "message" type
                    message = message.get("message")
                    # Creating the event by calling create_event() function
                    created_event = create_event_private_or_group_message(
                        siemplify,
                        alert_id,
                        message,
                    )

                elif "channel_post" in message:  # If the update is "channel_post" type
                    message = message["channel_post"]
                    # Creating the event by calling create_event() function
                    created_event = create_event_channel_message(
                        siemplify,
                        alert_id,
                        message,
                    )

                if created_event is not None:
                    # Creating the alert by calling create_alert() function
                    created_alert = create_alert(siemplify, alert_id, created_event)

                if created_alert is not None:
                    alerts.append(created_alert)
                    siemplify.LOGGER.info(f"Added Alert {alert_id} to package results")

        # If the telegram bot has no new messages to pull
        else:
            siemplify.LOGGER.info("There are no new messages")

        # Returning all the created alerts to the cases module in Siemplify

    except Exception as e:
        siemplify.LOGGER.error(f"Error occurred while running the connector: {e}")
        if "webhook" in str(e):
            siemplify.LOGGER.error(
                "Suspected active webhook for Telegram. "
                "You might need to deactivate it. "
                "You can do so with the next call: "
                "https://api.telegram.org/bot<bot_token>/setWebhook?url="
            )

    if not is_test_run:
        if all_messages_dict:
            try:
                last_update_id = int(all_messages_dict["result"][-1].get("update_id"))
                LastMessage(id=last_update_id).save(siemplify=siemplify)
            except Exception as err:
                siemplify.LOGGER.error(f"Can't save the last message id: {err}")
        else:
            siemplify.LOGGER.info("No messages found on updated")
    else:
        siemplify.LOGGER.info("*TEST RUN* - New update_id not saved")

    siemplify.return_package(alerts)


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
