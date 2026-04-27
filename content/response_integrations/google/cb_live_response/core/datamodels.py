from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict_keys, flat_dict_to_csv

ENRICHMENT_PREFIX = "CB_LIVE_RESPONSE"


class SessionStatus:
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    CLOSED = "CLOSE"


class CommandStatus:
    IN_PROGRESS = "in progress"
    PENDING = "pending"
    COMPLETED = "complete"
    CANCELED = "cancel"
    ERROR = "error"


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return self.to_json()

    def to_csv(self):
        flat_dict_to_csv(dict_to_flat(self.to_table()))


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        av_engine=None,
        av_status=None,
        id=None,
        av_last_scan_time=None,
        email=None,
        first_name=None,
        last_name=None,
        last_contact_time=None,
        last_device_policy_changed_time=None,
        last_external_ip_address=None,
        last_internal_ip_address=None,
        last_location=None,
        name=None,
        organization_id=None,
        organization_name=None,
        os=None,
        os_version=None,
        passive_mode=None,
        policy_id=None,
        policy_name=None,
        policy_override=None,
        quarantined=None,
        scan_status=None,
        sensor_out_of_date=None,
        sensor_states=None,
        sensor_version=None,
        status=None,
        **kwargs
    ):
        super().__init__(raw_data=raw_data)
        self.av_engine = av_engine
        self.av_status = av_status
        self.id = id
        self.av_last_scan_time = av_last_scan_time
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.last_contact_time = last_contact_time
        self.last_device_policy_changed_time = last_device_policy_changed_time
        self.last_external_ip_address = last_external_ip_address
        self.last_internal_ip_address = last_internal_ip_address
        self.last_location = last_location
        self.organization_id = organization_id
        self.name = name
        self.organization_name = organization_name
        self.os = os
        self.os_version = os_version
        self.passive_mode = passive_mode
        self.policy_id = policy_id
        self.policy_name = policy_name
        self.policy_override = policy_override
        self.quarantined = quarantined
        self.scan_status = scan_status
        self.sensor_out_of_date = sensor_out_of_date
        self.sensor_states = sensor_states
        self.sensor_version = sensor_version
        self.status = status

    def as_enrichment_data(self):
        enrichment_data = {
            "antivirus_last_scan_time": self.av_last_scan_time,
            "owner_email": self.email,
            "owner_first_name": self.first_name,
            "owner_last_name": self.last_name,
            "last_device_policy_changed_time": self.last_device_policy_changed_time,
            "device_os": self.os,
            "device_os_version": self.os_version,
            "scan_status": self.scan_status,
        }

        # Clear out None values
        enrichment_data = {k: v for k, v in enrichment_data.items() if v is not None}

        if self.policy_override:
            enrichment_data.update({"device_policy_override": self.policy_override})

        enrichment_data.update(
            {
                "device_id": self.id,
                "antivirus_status": ", ".join(self.av_status) if self.av_status else "",
                "last_contact_time": self.last_contact_time,
                "last_external_ip_address": self.last_external_ip_address,
                "last_internal_ip_address": self.last_internal_ip_address,
                "last_location": self.last_location,
                "full_device_name": self.name,
                "organization_id": self.organization_id,
                "organization_name": self.organization_name,
                "passive_mode": self.passive_mode,
                "device_policy_id": self.policy_id,
                "device_policy_name": self.policy_name,
                "quarantined": self.quarantined,
                "sensor_out_of_date": self.sensor_out_of_date,
                "sensor_states": (
                    ", ".join(self.sensor_states) if self.sensor_states else ""
                ),
                "sensor_version": self.sensor_version,
                "device_status": self.status,
            }
        )

        return add_prefix_to_dict_keys(dict_to_flat(enrichment_data), ENRICHMENT_PREFIX)


class Session(BaseModel):
    def __init__(self, raw_data, id=None, status=None, **kwargs):
        super().__init__(raw_data)
        self.status = status
        self.id = id

    @property
    def is_active(self):
        return self.status.lower() == SessionStatus.ACTIVE.lower()

    @property
    def is_pending(self):
        return self.status.lower() == SessionStatus.PENDING.lower()

    @property
    def is_closed(self):
        return self.status.lower() == SessionStatus.CLOSED.lower()


class LRSession(Session):
    def __init__(
        self,
        raw_data,
        id=None,
        sensor_id=None,
        status=None,
        create_time=None,
        hostname=None,
        address=None,
        session_timeout=None,
        os_version=None,
        current_working_directory=None,
        **kwargs
    ):
        super().__init__(raw_data, id, status)
        self.sensor_id = sensor_id
        self.create_time = create_time
        self.hostname = hostname
        self.address = address
        self.session_timeout = session_timeout
        self.os_version = os_version
        self.current_working_directory = current_working_directory


class Command(BaseModel):
    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        username=None,
        creation_time=None,
        completion_time=None,
        status=None,
        command_processes=None,
        command_files=None,
        details=None,
        memdump=None,
        execution_details=None,
        input_name=None,
        **kwargs
    ):
        super().__init__(raw_data)
        self.id = id
        self.name = name
        self.username = username
        self.creation_time = creation_time
        self.completion_time = completion_time
        self.status = status
        self.processes = command_processes
        self.files = command_files
        self.details = details
        self.memdump = memdump
        self.process_details = execution_details
        self.input_name = input_name

    @property
    def is_completed(self):
        return self.status.lower() == CommandStatus.COMPLETED.lower()

    @property
    def is_pending(self):
        return self.status.lower() == CommandStatus.PENDING.lower()

    @property
    def is_in_progress(self):
        return self.status.lower() == CommandStatus.IN_PROGRESS.lower()

    @property
    def is_failed(self):
        return self.status.lower() == CommandStatus.ERROR.lower()

    @property
    def is_canceled(self):
        return self.status.lower() == CommandStatus.CANCELED.lower()


class ListProcessesCommand(Command):
    def __init__(self, processes=None, **kwargs):
        super(ListProcessesCommand, self).__init__(**kwargs)
        self.processes = processes or []


class ListFilesCommand(Command):
    def __init__(self, raw_data, files=None, **kwargs):
        super().__init__(raw_data, **kwargs)
        self.files = files


class KillProcessCommand(Command):
    def __init__(self, pid=None, **kwargs):
        super(KillProcessCommand, self).__init__(**kwargs)
        self.pid = pid


class PutFileCommand(Command):
    def __init__(self, **kwargs):
        super(PutFileCommand, self).__init__(**kwargs)


class Process(BaseModel):
    def __init__(
        self,
        raw_data,
        pid=None,
        create_time=None,
        proc_guid=None,
        path=None,
        command_line=None,
        sid=None,
        username=None,
        parent=None,
        parent_guid=None,
        parent_create_time=None,
        **kwargs
    ):
        super().__init__(raw_data)
        self.pid = pid
        self.create_time = create_time
        self.proc_guid = proc_guid
        self.path = path
        self.command_line = command_line
        self.sid = sid
        self.username = username
        self.parent = parent
        self.parent_guid = parent_guid
        self.parent_create_time = parent_create_time

    def to_table(self):
        return {
            "Process ID": self.pid,
            "Creation Time": self.create_time,
            "Path": self.path,
            "Command Line": self.command_line,
            "SID": self.sid,
            "Username": self.username,
            "Parent Process": self.parent,
            "Parent Process Creation Time": self.parent_create_time,
        }


class UploadFile:
    def __init__(
        self,
        raw_data,
        id=None,
        size=None,
        file_name=None,
        size_uploaded=None,
        upload_url=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.size = size
        self.file_name = file_name
        self.size_uploaded = size_uploaded
        self.upload_url = upload_url


class ProcessV6(BaseModel):
    def __init__(
        self,
        raw_data,
        process_pid=None,
        process_create_time=None,
        process_path=None,
        process_cmdline=None,
        sid=None,
        process_username=None,
        parent_pid=None,
        parent_create_time=None,
        **kwargs
    ):
        super().__init__(raw_data)
        self.pid = process_pid
        self.path = process_path
        self.command_line = process_cmdline
        self.sid = sid
        self.username = process_username
        self.parent = parent_pid
        self.parent_create_time = parent_create_time
        self.create_time = process_create_time

    def to_table(self):
        return {
            "Process ID": self.pid,
            "Creation Time": self.create_time,
            "Path": self.path,
            "Command Line": self.command_line,
            "SID": self.sid,
            "Username": self.username,
            "Parent Process": self.parent,
            "Parent Process Creation Time": self.parent_create_time,
        }

    def to_json(self):
        return {
            "command_line": self.command_line,
            "create_time": self.create_time,
            "parent": self.parent,
            "parent_create_time": self.parent_create_time,
            "path": self.path,
            "pid": self.pid,
            "sid": self.sid,
            "username": self.username,
        }


class File(BaseModel):
    def __init__(
        self,
        raw_data,
        size=None,
        attributes=None,
        filename=None,
        alternate_name=None,
        create_time=None,
        last_access_time=None,
        last_write_time=None,
        **kwargs
    ):
        super().__init__(raw_data)
        self.size = size
        self.attributes = attributes
        self.filename = filename
        self.alternate_name = alternate_name
        self.create_time = create_time
        self.last_access_time = last_access_time
        self.last_write_time = last_write_time

    def to_table(self):
        return {
            "Filename": self.filename,
            "Alternate Name": self.alternate_name,
            "Size": str(self.size),
            "Attributes": "; ".join(self.attributes) if self.attributes else [],
            "Create time": str(self.create_time),
            "Last access time": str(self.last_access_time),
            "Last write time": str(self.last_write_time),
        }


class FileDetails(BaseModel):
    def __init__(self, raw_data, file_id=None, **kwargs):
        super().__init__(raw_data)
        self.file_id = file_id


class StorageFile(BaseModel):
    def __init__(
        self,
        raw_data,
        id=None,
        file_name=None,
        size=None,
        size_uploaded=None,
        upload_url=None,
        **kwargs
    ):
        super().__init__(raw_data)
        self.id = id
        self.size = str(size)
        self.filename = file_name
        self.size_uploaded = str(size_uploaded)
        self.upload_url = upload_url

    def to_table(self):
        return {
            "ID": self.id,
            "File Name": self.filename,
            "Size": self.size,
            "Size Uploaded": self.size_uploaded,
            "Upload URL": self.upload_url,
        }


class Memdump(BaseModel):
    def __init__(
        self,
        raw_data,
        compressing=None,
        complete=None,
        dumping=None,
        return_code=None,
        percentdone=None,
        **kwargs
    ):
        super().__init__(raw_data)
        self.compressing = compressing
        self.complete = complete
        self.dumping = dumping
        self.return_code = return_code
        self.percentdone = percentdone


class ProcessDetail(BaseModel):
    def __init__(self, raw_data, pid=None, return_code=None, **kwargs):
        super().__init__(raw_data)
        self.pid = pid
        self.return_code = return_code
