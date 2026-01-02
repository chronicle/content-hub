from __future__ import annotations

import time

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.adapter import PlaybookAdapter
from ..core.config import Config
from ..core.utils_manager import GIBConnector


@output_handler
def main():
    # Google Chronicle base class initialization
    siemplify = SiemplifyAction()

    # Google Chronicle base class set up
    siemplify.script_name = Config.GC_COLLECTION_SCRIPT_NAME

    # Get basic collection configuration
    mapping_parser_enabled = extract_action_param(
        siemplify, param_name="Enable mapping parser", print_value=True
    )
    collection = extract_action_param(siemplify, param_name="Collection", print_value=True)
    start_date = extract_action_param(siemplify, param_name="Start date", print_value=True)
    limit = extract_action_param(siemplify, param_name="Portion limit", print_value=True)

    # Get poller
    connector = GIBConnector(siemplify)
    poller = connector.init_action_poller()

    siemplify.LOGGER.info("──── GATHER SEQUPDATE")

    # Extract sequence update number from storage
    fetched_ts = siemplify.fetch_timestamp(datetime_format=False, timezone=False)
    siemplify.LOGGER.info("fetch_ts: {}".format(fetched_ts))

    if fetched_ts:
        # Get start sequence update number from storage
        init_seq_update = fetched_ts
    else:
        # Set start date 1 day back if None
        if not start_date:
            start_date = PlaybookAdapter.get_default_date(days=1)

        siemplify.LOGGER.info("Start date: {}".format(start_date))

        # Get start sequence update number from API
        _seq_update_dict = poller.get_seq_update_dict(date=start_date, collection_name=collection)
        init_seq_update = _seq_update_dict.get(collection, None)

    siemplify.LOGGER.info("Sequence update number: {}".format(_seq_update_dict))

    # Create generator
    generator = poller.create_update_generator(
        collection_name=collection, sequpdate=init_seq_update, limit=int(limit)
    )

    # Sleep to keep API active
    time.sleep(1)

    siemplify.LOGGER.info("──── PARSE DATA")

    # Create result holder
    result_json = {}

    # Data storage for chosen collection
    result_name = collection.replace("/", "_")
    result_json[result_name] = []

    # Parse data
    for portion in generator:
        if mapping_parser_enabled == "true":
            # Extract data and parse it using mapping keys
            parsed_portion = portion.parse_portion()
        else:
            # Extract data and collect raw dict items
            parsed_portion = portion.raw_dict.get("items")

        # Fill in result holder
        result_json[result_name].extend(parsed_portion)

        # Sleep to keep API active
        time.sleep(1)

        siemplify.LOGGER.info(parsed_portion)

    # Add result to Google Chronicle base class
    siemplify.result.add_result_json(result_json)

    siemplify.LOGGER.info("──── END THE TASK")

    # Prepare output message
    output_message = (
        "output message : All is done"  # human-readable message, showed in UI as the action result
    )
    result_value = True  # Set a simple result value, used for playbook if\else and placeholders.
    status = (
        EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    )

    siemplify.LOGGER.info(
        "\n  status: {}\n  result_value: {}\n  output_message: {}".format(
            status, result_value, output_message
        )
    )

    # End the playbook
    siemplify.end(output_message, result_value=result_value, execution_state=status)


if __name__ == "__main__":
    main()
