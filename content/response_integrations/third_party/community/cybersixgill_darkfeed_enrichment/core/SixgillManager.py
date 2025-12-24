from __future__ import annotations

from sixgill.sixgill_enrich_client import SixgillEnrichClient

PROVIDER = "Cybersixgill Darkfeed Enrichment"
SIXGILL_CHANNEL_ID = "1f4fdd520d3a721799fc0d044283d364"


class SixgillManagerError(Exception):
    """Exception for Sixgill Manager"""


class SixgillEnrichManager:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def create_sixgill_client(self):
        sixgill_darkfeed_client = None
        try:
            sixgill_darkfeed_client = SixgillEnrichClient(
                self.client_id,
                self.client_secret,
                SIXGILL_CHANNEL_ID,
            )
        except Exception as err:
            raise SixgillManagerError(f"create_sixgill_client Error - {err}")
        return sixgill_darkfeed_client

    def query_sixgill(self, entity_type, entity_value):
        status = False
        enrich_indicators = None
        try:
            enrich_client = self.create_sixgill_client()
            entity_value = entity_value.strip()
            enrich_indicators = enrich_client.enrich_actor(entity_value)
            if enrich_indicators:
                pass
            else:
                enrich_indicators = enrich_client.enrich_ioc(entity_type, entity_value)
            status = True
        except Exception as err:
            raise SixgillManagerError(
                f" query_sixgill Error - Entity - {entity_value} - {err}",
            )
        return status, enrich_indicators
