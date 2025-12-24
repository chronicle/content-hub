from __future__ import annotations

from sixgill.sixgill_base_client import SixgillBaseClient
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

PROVIDER = "Cybersixgill"
Sixgill_Channel_Id = "1f4fdd520d3a721799fc0d044283d364"


class SixgillManagerError(Exception):
    """Exception for Sixgill Manager"""


class SixgillEnrichManager:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def create_sixgill_client(self):
        try:
            sixgill_client = SixgillBaseClient(
                self.client_id,
                self.client_secret,
                Sixgill_Channel_Id,
            )
            sixgill_access_token = sixgill_client.get_access_token()
            if sixgill_access_token:
                status = EXECUTION_STATE_COMPLETED
                msg = "Successfully Connected to Sixgill"
                result = True
        except Exception as err:
            status = EXECUTION_STATE_FAILED
            msg = f"Failed to connect to Cybersixgill with error {err}"
            result = False
            raise SixgillManagerError(f"create_sixgill_client Error - {err}")
        return status, msg, result
