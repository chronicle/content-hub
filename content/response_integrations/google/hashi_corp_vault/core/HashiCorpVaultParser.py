from __future__ import annotations
from hashi_corp_vault.core.datamodels import *


class HashiCorpVaultParser:
    @staticmethod
    def build_key_value_response_object(raw_data):
        return KeyValueResponse(
            raw_data=raw_data, keys=raw_data.get("data", {}).get("keys", [])
        )

    @staticmethod
    def build_generic_response_object(raw_data):
        return GenericResponse(raw_data=raw_data, data=raw_data.get("data"))
