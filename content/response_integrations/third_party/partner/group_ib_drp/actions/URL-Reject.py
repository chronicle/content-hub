from __future__ import annotations
import time

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED, EXECUTION_STATE_TIMEDOUT

# Import Managers
from ..core.config import Config
from ..core.UtilsManager import GIBConnector


@output_handler
def main():
    # Google Chronicle base class initialization
    siemplify = SiemplifyAction()

    # Google Chronicle base class set up
    siemplify.script_name = Config.GC_REJECT_SCRIPT_NAME

    # Get poller
    poller = GIBConnector(siemplify).init_action_poller()

    siemplify.LOGGER.info('──── GATHER ENTITIES')
    
    # Gather received entities and detect their type return [(entity.identifier, type), ...]
    received_entities = [(entity.identifier, entity.entity_type) for entity in siemplify.target_entities]

    siemplify.LOGGER.info('──── PARSE DATA')

    # Build URL → UID lookup once from event data
    url_to_uid = {}
    for event in siemplify.current_alert.security_events:
        props = getattr(event, 'additional_properties', {}) or {}
        url = props.get("violation_url", "").lower()
        uid_val = props.get("violation_uid", "")
        if url and uid_val and url not in url_to_uid:
            url_to_uid[url] = uid_val

    # Gather data
    for _entity, _entity_type in received_entities:

        siemplify.LOGGER.info("entity: {}, type: {}".format(_entity, _entity_type))

        if _entity and _entity_type == "DestinationURL":
            uid = url_to_uid.get(_entity.lower())

            if not uid:
                siemplify.LOGGER.error("No violation UID found for entity: {}".format(_entity))
                continue

            data = {"violationId": uid, "approve": False}
            params = {"q": None}
            
            siemplify.LOGGER.info("data: {}".format(data))
            
            # Extract data
            res = poller.send_request(endpoint="violation/change-approve", params=params, method="POST", json=data)
            
            siemplify.LOGGER.info(res)

            # Sleep to keep API active
            time.sleep(1)
    
    siemplify.end('done', 'done')


if __name__ == "__main__":
    main()
