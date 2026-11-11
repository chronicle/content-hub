from __future__ import annotations
from sentinel_one_v2.core.SentinelOneV2Manager import SentinelOneV2Manager
from sentinel_one_v2.core.SentinelOneV2ManagerV2 import SentinelOneV2ManagerV2
from sentinel_one_v2.core.exceptions import SentinelOneV2UnsupportedApiVersionError

API_VERSION_2_0 = "2.0"
API_VERSION_2_1 = "2.1"
SUPPORTED_API_VERSIONS = [API_VERSION_2_0, API_VERSION_2_1]


class SentinelOneV2ManagerFactory:
    def __init__(self, api_version=API_VERSION_2_1):
        self.api_version = get_api_version_or_raise(api_version)

    def get_manager(self, *args, **kwargs):
        kwargs["api_version"] = self.api_version

        if self.api_version == API_VERSION_2_0:
            return SentinelOneV2Manager(*args, **kwargs)

        if self.api_version == API_VERSION_2_1:
            return SentinelOneV2ManagerV2(*args, **kwargs)


def get_api_version_or_raise(version_to_check):
    """
    Check if version is supported
    :param version_to_check: {float}
    """
    if version_to_check not in SUPPORTED_API_VERSIONS:
        raise SentinelOneV2UnsupportedApiVersionError(SUPPORTED_API_VERSIONS)

    return version_to_check
