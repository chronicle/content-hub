from __future__ import annotations

from sixgill.sixgill_base_client import SixgillBaseClient
from sixgill.sixgill_enrich_client import SixgillEnrichClient
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

PROVIDER = "Cybersixgill"
SIXGILL_CHANNEL_ID = "1f4fdd520d3a721799fc0d044283d364"


class SixgillManagerError(Exception):
    """Exception for Sixgill Manager"""


class SixgillEnrichManager:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def test_connectivity(self):
        result = False
        try:
            sixgill_darkfeed_client = SixgillBaseClient(
                self.client_id,
                self.client_secret,
                SIXGILL_CHANNEL_ID,
            )
            sixgill_access_token = sixgill_darkfeed_client.get_access_token()
            if sixgill_access_token:
                status = EXECUTION_STATE_COMPLETED
                msg = "Successfully Connected to Sixgill"
                result = True
        except Exception as err:
            msg = f"Connectivity Failed Error - {err}"
            status = EXECUTION_STATE_FAILED
            self.siemplify.LOGGER.error(f"test_connectivity Error - {err}")
        return status, msg, result

    def create_sixgill_client(self):
        status = False
        sixgill_dve_client = None
        try:
            sixgill_dve_client = SixgillEnrichClient(
                self.client_id,
                self.client_secret,
                SIXGILL_CHANNEL_ID,
            )
        except Exception as err:
            raise SixgillManagerError(f"create_sixgill_client Error - {err}")
        return sixgill_dve_client

    def query_sixgill(self, entity_value):
        enrich_cve = None
        try:
            enrich_client = self.create_sixgill_client()
            entity_value = entity_value.strip()
            enrich_cve = enrich_client.enrich_dve(entity_value)
        except Exception as err:
            raise SixgillManagerError(
                f" query_sixgill Error - Entity - {entity_value} - {err}",
            )
        return enrich_cve
