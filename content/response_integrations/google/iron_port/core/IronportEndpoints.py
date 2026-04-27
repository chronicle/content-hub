from __future__ import annotations
from urllib.parse import urljoin


class IronportEndpoints:
    headers = {"Content-Type": "application/json"}
    api_host_format = "esa/api/v2.0/"

    @staticmethod
    def get_login(api_root):
        return urljoin(api_root, "login")

    @staticmethod
    def get_messages(api_root):
        return urljoin(api_root, "message-tracking/messages")

    @staticmethod
    def get_reports(api_root, report_type):
        return urljoin(api_root, f"reporting/{report_type}")
