from __future__ import annotations
from .datamodels import (
    Device,
    Session,
    LRSession,
    ListProcessesCommand,
    Process,
    KillProcessCommand,
    Command,
    ListFilesCommand,
    File,
    ProcessV6,
    PutFileCommand,
    UploadFile,
    FileDetails,
    StorageFile,
    Memdump,
    ProcessDetail,
)
from copy import deepcopy
from .constants import API_VERSION_V3, API_VERSION_V6


class CBLiveResponseParser:
    """
    CB Live Response Transformation Layer.
    """

    def build_results(
        self, raw_json, method, data_key="data", pure_data=False, limit=None, **kwargs
    ):
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[
                :limit
            ]
        ]

    @staticmethod
    def build_siemplify_device_obj(device_data):
        return Device(raw_data=device_data, **device_data)

    @staticmethod
    def build_siemplify_session_obj(session_data):
        return Session(raw_data=session_data, **session_data)

    @staticmethod
    def build_siemplify_lr_session_obj(session_data):
        return LRSession(raw_data=session_data, **session_data)

    @staticmethod
    def build_siemplify_process_obj(process_data, version):
        if version == API_VERSION_V3:
            return Process(raw_data=process_data, **process_data)
        elif version == API_VERSION_V6:
            return ProcessV6(raw_data=process_data, **process_data)

    def build_siemplify_command_obj(
        self, command_data, start_from=0, limit=None, version=API_VERSION_V3
    ):
        raw_data = deepcopy(command_data)
        limited_files = (
            command_data.get("files", [])[start_from : limit + start_from]
            if limit
            else command_data.get("files", [])[start_from:]
        )
        processes = command_data.get("processes", [])[:limit]
        details = self.build_details_obj(raw_data, version)
        raw_data.update({"files": limited_files, "processes": processes})
        return Command(
            raw_data=raw_data,
            command_files=[
                self.build_siemplify_file_obj(file) for file in limited_files
            ],
            command_processes=[
                self.build_siemplify_process_obj(process, version=version)
                for process in processes
            ],
            details=self.build_siemplify_file_details_obj(details),
            input_name=self.get_directory_name(raw_data=raw_data, api_version=version),
            **command_data
        )

    def get_directory_name(self, raw_data, api_version=API_VERSION_V3):
        if api_version == API_VERSION_V3:
            return raw_data.get("obj", {}).get("object", "")
        else:
            return raw_data.get("input", {}).get("object", "")

    def get_files_objects(self, raw_data, start_from, limit=None):
        data = self.build_results(
            raw_data, method="build_siemplify_storage_file_obj", pure_data=True
        )
        data.reverse()
        return data[start_from : limit + start_from] if limit else data[start_from:]

    @staticmethod
    def build_details_obj(raw_data, version):
        if version == API_VERSION_V3:
            return {"file_id": raw_data.get("file_id")}

        if version == API_VERSION_V6:
            return raw_data.get("file_details", {})

    @staticmethod
    def build_siemplify_file_details_obj(raw_data):
        return FileDetails(raw_data, **raw_data)

    def build_siemplify_process_command_obj(
        self, command_data, process_name=None, limit=None, version=API_VERSION_V3
    ):
        raw_data = deepcopy(command_data)
        processes = command_data.get("processes", [])[:limit]
        if process_name:
            processes = self.filter_processes(processes, version, process_name)

        raw_data.update({"processes": processes})
        return Command(
            raw_data=raw_data,
            command_processes=[
                self.build_siemplify_process_obj(process, version)
                for process in processes
                if process
            ],
            **command_data
        )

    def build_siemplify_memdump_command_obj(self, command_data, version=API_VERSION_V3):
        raw_data = deepcopy(command_data)

        return Command(
            raw_data=raw_data,
            memdump=self.build_memdump_obj(raw_data, version),
            **command_data
        )

    def build_siemplify_execute_file_command_obj(
        self, command_data, version=API_VERSION_V3
    ):
        raw_data = deepcopy(command_data)

        return Command(
            raw_data=raw_data,
            execution_details=self.build_execute_file_obj(raw_data, version),
            **command_data
        )

    def build_execute_file_obj(self, raw_data, version):
        data = {}
        if version == API_VERSION_V3:
            data = {
                "pid": raw_data.get("pid", ""),
                "return_code": raw_data.get("return_code", ""),
            }
        if version == API_VERSION_V6:
            data = raw_data.get("process_details", {})
        return ProcessDetail(data, **data)

    @staticmethod
    def build_memdump_obj(raw_json, version):
        if version == API_VERSION_V6:
            raw_data = raw_json.get("mem_dump")
            return Memdump(raw_data, **raw_data)
        if version == API_VERSION_V3:
            data = {
                "compressing": raw_json.get("compressing"),
                "complete": raw_json.get("complete"),
                "dumping": raw_json.get("dumping"),
                "return_code": raw_json.get("return_code"),
                "percentdone": raw_json.get("percentdone"),
            }
            return Memdump(data, **data)

    @staticmethod
    def filter_processes(processes, version, process_name):
        key = "command_line" if version == API_VERSION_V3 else "process_cmdline"

        return [
            proc
            for proc in processes
            if process_name.lower() in str(proc.get(key, "")).lower()
        ]

    @staticmethod
    def build_siemplify_list_processes_command_obj(command_data):
        raw_data = deepcopy(command_data)
        processes = [
            CBLiveResponseParser.build_siemplify_process_obj(process)
            for process in command_data.pop("processes", [])
        ]
        return ListProcessesCommand(
            raw_data=raw_data, processes=processes, **command_data
        )

    def build_siemplify_list_files_command_obj(self, command_data):
        files = self.build_results(
            raw_json=command_data.get("files", []),
            method="build_siemplify_file_obj",
            pure_data=True,
        )
        return ListFilesCommand(raw_data=command_data, files=files, **command_data)

    def build_siemplify_file_obj(self, raw_data):
        return File(raw_data=raw_data, **raw_data)

    @staticmethod
    def build_siemplify_kill_process_command_obj(command_data):
        return KillProcessCommand(raw_data=command_data, **command_data)

    @staticmethod
    def get_reason(raw_json):
        return raw_json.get("reason")

    def get_results(self, raw_json, builder_method=None):
        resources = raw_json.get("results", [])
        return (
            [
                getattr(self, builder_method)(resource_json)
                for resource_json in resources
            ]
            if builder_method
            else resources
        )

    def build_siemplify_upload_file_obj(self, file_data):
        return UploadFile(raw_data=file_data, **file_data)

    def build_siemplify_put_file_command_obj(self, command_data):
        return PutFileCommand(raw_data=command_data, **command_data)

    @staticmethod
    def build_siemplify_storage_file_obj(raw_data):
        return StorageFile(raw_data, **raw_data)
