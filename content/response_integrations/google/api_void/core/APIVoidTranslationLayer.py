from __future__ import annotations
from .datamodels import (
    DomainReputation,
    EmailInformation,
    IPReputation,
    Screenshot,
    URLReputation,
)


class APIVoidTranslationLayer:
    @staticmethod
    def build_ip_reputation_obj(raw_data):
        return IPReputation(raw_data)

    @staticmethod
    def build_domain_reputation_obj(raw_data):
        return DomainReputation(raw_data)

    @staticmethod
    def build_url_reputation_obj(raw_data):
        return URLReputation(raw_data)

    @staticmethod
    def build_screenshot_obj(raw_data):
        return Screenshot(raw_data, **raw_data)

    @staticmethod
    def build_email_information_obj(raw_data):
        return EmailInformation(raw_data, **raw_data)
