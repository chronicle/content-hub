from __future__ import annotations
from .datamodels import *


class SymantecEmailSecurityCloudParser:
    def build_ioc_results_list(self, raw_data):
        return [self.build_ioc_result(item) for item in raw_data]

    def build_ioc_result(self, raw_data):
        return IOCResult(
            raw_data=raw_data,
            blacklist_id=raw_data.get("iocBlackListId"),
            ioc_type=raw_data.get("iocType"),
            ioc_value=raw_data.get("iocValue"),
            failure_reason=raw_data.get("failureReason"),
        )
