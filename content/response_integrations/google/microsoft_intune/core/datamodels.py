from __future__ import annotations

from TIPCommon import dict_to_flat


class BaseModel:

    def __init__(self, raw_data: dict) -> None:
        self.raw_data = raw_data

    def to_json(self) -> dict:
        return self.raw_data

    def to_flat(self) -> dict:
        return dict_to_flat(self.to_json())


class GetManageDeviceData(BaseModel):
    """
    Class to create data model for Get Manage Device
    """

    def __init__(self, raw_data: dict) -> None:
        super().__init__(raw_data)


class ListManagedDevices(BaseModel):
    """
    Class to create data model for Locate Managed Device
    """

    def __init__(self, raw_data: dict, devices, count) -> None:
        super().__init__(raw_data)
        self.devices = devices
        self.count = count


class Device(BaseModel):
    """
    Class to create data model for List Manage Device
    """

    def __init__(
        self,
        item_data,
        device_id: str,
        user_id: str,
        device_name: str,
        operating_system: str,
        compliance_state: str,
        enrolled_date: str,
        last_sync_date: str,
    ) -> None:
        super().__init__(item_data)
        self.device_id = device_id
        self.user_id = user_id
        self.host_name = device_name
        self.operating_system = operating_system
        self.compliance_state = compliance_state
        self.enrolled_date = enrolled_date
        self.last_sync_date = last_sync_date

    def to_csv(self) -> dict[str, str]:
        device_data = {
            "Last Sync Date Time": self.last_sync_date,
            "Enrolled Date Time": self.enrolled_date,
            "Compliance State": self.compliance_state,
            "Operating System": self.operating_system,
            "Device Name": self.host_name,
            "User ID": self.user_id,
            "ID": self.device_id,
        }
        return dict_to_flat(device_data)
