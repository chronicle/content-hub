from __future__ import annotations
from TIPCommon import dict_to_flat


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return self.to_flat()


class Account(BaseModel):
    def to_csv(self):
        flat_dict = self.to_flat()
        return {
            "Id": flat_dict.get("id"),
            "Safe Name": flat_dict.get("safeName"),
            "User Name": flat_dict.get("userName"),
            "Secret Type": flat_dict.get("secretType"),
        }
