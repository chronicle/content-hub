from __future__ import annotations
from .datamodels import Account


class CyberArkPamParser:
    def build_account(self, account_json):
        return Account(account_json)

    def build_accounts(self, json_response):
        accounts_json = json_response["value"]
        return [self.build_account(account_json) for account_json in accounts_json]
