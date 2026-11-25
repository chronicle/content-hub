# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Domains:
    def __init__(self, raw_data, domains=None):
        self.raw_data = raw_data
        self.domains = domains

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())


class IPs:
    def __init__(self, raw_data, ips=None):
        self.raw_data = raw_data
        self.ips = ips

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())


class IOCS(BaseModel):
    def __init__(
        self,
        raw_data=None,
        alert_table=None,
        evaluation_date=None,
        ioc_context=None,
        ioc_triggered_on_machine=None,
        bias_status=None,
        active=None,
        description=None,
        ioc_type=None,
        ioc_level=None,
        last_executed=None,
        name=None,
        priority=None,
        query=None,
        machine_count=None,
        module_count=None,
    ):
        super(IOCS, self).__init__(raw_data)
        self.alert_table = alert_table
        self.evaluation_date = evaluation_date
        self.ioc_context = ioc_context
        self.ioc_triggered_on_machine = ioc_triggered_on_machine
        self.bias_status = bias_status
        self.active = active
        self.description = description
        self.ioc_type = ioc_type
        self.ioc_level = ioc_level
        self.last_executed = last_executed
        self.name = name
        self.priority = priority
        self.query = query
        self.machine_count = machine_count
        self.module_count = module_count

    def to_enrichment_data(self, prefix=None):
        new_dict = {
            "Alertable": self.alert_table,
            "EvaluationDate": self.evaluation_date,
            "IOCContext": self.ioc_context,
            "IOCTriggeredOnMachine": self.ioc_triggered_on_machine,
            "BiasStatus": self.bias_status,
            "Active": self.active,
            "Description": self.description,
            "Type": self.ioc_type,
            "IOCLevel": self.ioc_level,
            "LastExecuted": self.last_executed,
            "Name": self.name,
            "Priority": self.priority,
            "Query": self.query,
            "MachineCount": self.machine_count,
            "ModuleCount": self.module_count,
        }
        data = dict_to_flat(new_dict)
        return add_prefix_to_dict(data, prefix) if prefix else data


class IOCLevel(BaseModel):
    def __init__(
        self,
        raw_data=None,
        alert_table=None,
        priority=None,
        query=None,
        active=None,
        user_defined=None,
        whitelisted_count=None,
        persistent=None,
        name=None,
        machine_count=None,
        module_count=None,
        blacklisted_count=None,
        graylisted_count=None,
        description=None,
        error_message=None,
        evaluation_machine_count=None,
        ioc_type=None,
        ioc_level=None,
        last_evaluation_duration=None,
        last_execution_duration=None,
        last_executed=None,
    ):
        super(IOCLevel, self).__init__(raw_data)

        self.active = active
        self.alert_table = alert_table
        self.blacklisted_count = blacklisted_count
        self.graylisted_count = graylisted_count
        self.description = description
        self.error_message = error_message
        self.evaluation_machine_count = evaluation_machine_count
        self.ioc_type = ioc_type
        self.ioc_level = ioc_level
        self.last_evaluation_duration = last_evaluation_duration
        self.last_execution_duration = last_execution_duration
        self.last_executed = last_executed
        self.machine_count = machine_count
        self.module_count = module_count
        self.name = name
        self.persistent = persistent
        self.priority = priority
        self.query = query
        self.user_defined = user_defined
        self.whitelisted_count = whitelisted_count

    def to_enrichment_data(self, prefix=None):
        new_dict = {
            "Active": self.active,
            "Alertable": self.alert_table,
            "BlacklistedCount": self.blacklisted_count,
            "GraylistedCount": self.graylisted_count,
            "Description": self.description,
            "ErrorMessage": self.error_message,
            "EvaluationMachineCount": self.evaluation_machine_count,
            "Type": self.ioc_type,
            "IOCLevel": self.ioc_level,
            "LastEvaluationDuration": self.last_evaluation_duration,
            "LastExecutionDuration": self.last_execution_duration,
            "LastExecuted": self.last_executed,
            "MachineCount": self.machine_count,
            "ModuleCount": self.module_count,
            "Name": self.name,
            "Persistent": self.persistent,
            "Priority": self.priority,
            "Query": self.query,
            "UserDefined": self.user_defined,
            "WhitelistedCount": self.whitelisted_count,
        }
        data = dict_to_flat(new_dict)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Machine(BaseModel):

    def __init__(
        self,
        raw_data=None,
        driver_error_code=None,
        servicepack_os=None,
        machine_status=None,
        machine_type=None,
        version_info=None,
        username=None,
        organization_unit=None,
        local_ip=None,
        network_segment=None,
        gateway=None,
        remote_ip=None,
        group=None,
        admin_status=None,
        kernel_debugger_detected=None,
        early_start=None,
        notify_shutdown_module=None,
        loaded_module_module=None,
        notify_routine_module=None,
        unloaded_driver_module=None,
        error_log_module=None,
        low_level_reader_module=None,
        process_module=None,
        worker_thread_module=None,
        windows_hooks_module=None,
        debugger_attached_to_process=None,
        process_monitor_module=None,
        thread_monitor_module=None,
        object_monitor_module=None,
        image_monitor_module=None,
        driver_monitor_module=None,
        idi_monitor_module=None,
        tracking_module=None,
        tracking_registry_monitor=None,
        tracking_object_monitor=None,
        tracking_file_monitor=None,
        tracking_remote_thread_monitor=None,
        tracking_create_process_monitor=None,
        tracking_hard_link_monitor=None,
        tracking_file_block_monitor=None,
        tracking_network_monitor=None,
        ecat_server_name=None,
        online=None,
        iioc_score=None,
        chassis_type=None,
        containment_supported=None,
        agent_id=None,
        bios=None,
        os_build_number=None,
        comment=None,
        connection_time=None,
        language=None,
        dns=None,
        domain_role=None,
        ecat_service_compile_time=None,
        ecat_package_time=None,
        start_time=None,
        ecat_driver_compile_time=None,
        domain_name=None,
        idle=None,
        include_in_monitoring=None,
        include_in_schedule=None,
        installation_failed=None,
        install_time=None,
        iioc_level0=None,
        iioc_level1=None,
        iioc_level2=None,
        iioc_level3=None,
        country=None,
        boot_time=None,
        last_scan=None,
        last_seen=None,
        mac=None,
        machine_id=None,
        machine_name=None,
        allow_access_data_source_domain=None,
        allow_display_mixed_content=None,
        antivirus_disabled=None,
        bad_certificate_warning_disabled=None,
        cookies_cleanup_disabled=None,
        crossite_script_filter_disabled=None,
        firewall_disabled=None,
        iedep_disabled=None,
        ieenhanced_security_disabled=None,
        intranet_zone_notification_disabled=None,
        lua_disabled=None,
        no_antivirus_notification_disabled=None,
        no_firewall_notification_disabled=None,
        no_uac_notification_disabled=None,
        no_windows_update_disabled=None,
        registry_tools_disabled=None,
        smart_screen_filter_disabled=None,
        system_restore_disabled=None,
        task_manager_disabled=None,
        uac_disabled=None,
        warning_on_zone_crossing_disabled=None,
        warning_post_redirection_disabled=None,
        manufacturer=None,
        model=None,
        network_adapter_promisc_mode=None,
        operating_system=None,
        processor_architecture=None,
        processor_count=None,
        platform=None,
        processor_is_32_bits=None,
        processor_is_64=None,
        processor_name=None,
        scanning=None,
        scan_start_time=None,
        serial=None,
        timezone=None,
        total_physical_memory=None,
        https_fallback_mode=None,
        blocking_active=None,
        roaming_agents_relay_system_active=None,
        user_id=None,
        windows_directory=None,
        netwitness_investigate=None,
        containment_status=None,
    ):
        super(Machine, self).__init__(raw_data)
        self.driver_error_code = driver_error_code
        self.servicepack_os = servicepack_os
        self.machine_status = machine_status
        self.machine_type = machine_type
        self.version_info = version_info
        self.username = username
        self.organization_unit = organization_unit
        self.local_ip = local_ip
        self.network_segment = network_segment
        self.gateway = gateway
        self.remote_ip = remote_ip
        self.group = group
        self.admin_status = admin_status
        self.kernel_debugger_detected = kernel_debugger_detected
        self.early_start = early_start
        self.notify_shutdown_module = notify_shutdown_module
        self.loaded_module_module = loaded_module_module
        self.notify_routine_module = notify_routine_module
        self.unloaded_driver_module = unloaded_driver_module
        self.error_log_module = error_log_module
        self.low_level_reader_module = low_level_reader_module
        self.process_module = process_module
        self.worker_thread_module = worker_thread_module
        self.windows_hooks_module = windows_hooks_module
        self.debugger_attached_to_process = debugger_attached_to_process
        self.process_monitor_module = process_monitor_module
        self.thread_monitor_module = thread_monitor_module
        self.object_monitor_module = object_monitor_module
        self.image_monitor_module = image_monitor_module
        self.driver_monitor_module = driver_monitor_module
        self.idi_monitor_module = idi_monitor_module
        self.tracking_module = tracking_module
        self.tracking_registry_monitor = tracking_registry_monitor
        self.tracking_object_monitor = tracking_object_monitor
        self.tracking_file_monitor = tracking_file_monitor
        self.tracking_remote_thread_monitor = tracking_remote_thread_monitor
        self.tracking_create_process_monitor = tracking_create_process_monitor
        self.tracking_hard_link_monitor = tracking_hard_link_monitor
        self.tracking_file_block_monitor = tracking_file_block_monitor
        self.tracking_network_monitor = tracking_network_monitor
        self.ecat_server_name = ecat_server_name
        self.online = online
        self.iioc_score = iioc_score
        self.chassis_type = chassis_type
        self.containment_supported = containment_supported
        self.agent_id = agent_id
        self.bios = bios
        self.os_build_number = os_build_number
        self.comment = comment
        self.connection_time = connection_time
        self.language = language
        self.dns = dns
        self.domain_role = domain_role
        self.ecat_service_compile_time = ecat_service_compile_time
        self.ecat_package_time = ecat_package_time
        self.start_time = start_time
        self.ecat_driver_compile_time = ecat_driver_compile_time
        self.domain_name = domain_name
        self.idle = idle
        self.include_in_monitoring = include_in_monitoring
        self.include_in_schedule = include_in_schedule
        self.installation_failed = installation_failed
        self.install_time = install_time
        self.iioc_level0 = iioc_level0
        self.iioc_level1 = iioc_level1
        self.iioc_level2 = iioc_level2
        self.iioc_level3 = iioc_level3
        self.country = country
        self.boot_time = boot_time
        self.last_scan = last_scan
        self.last_seen = last_seen
        self.mac = mac
        self.machine_id = machine_id
        self.machine_name = machine_name
        self.allow_access_data_source_domain = allow_access_data_source_domain
        self.allow_display_mixed_content = allow_display_mixed_content
        self.antivirus_disabled = antivirus_disabled
        self.bad_certificate_warning_disabled = bad_certificate_warning_disabled
        self.cookies_cleanup_disabled = cookies_cleanup_disabled
        self.crossite_script_filter_disabled = crossite_script_filter_disabled
        self.firewall_disabled = firewall_disabled
        self.iedep_disabled = iedep_disabled
        self.ieenhanced_security_disabled = ieenhanced_security_disabled
        self.intranet_zone_notification_disabled = intranet_zone_notification_disabled
        self.lua_disabled = lua_disabled
        self.no_antivirus_notification_disabled = no_antivirus_notification_disabled
        self.no_firewall_notification_disabled = no_firewall_notification_disabled
        self.no_uac_notification_disabled = no_uac_notification_disabled
        self.no_windows_update_disabled = no_windows_update_disabled
        self.registry_tools_disabled = registry_tools_disabled
        self.smart_screen_filter_disabled = smart_screen_filter_disabled
        self.system_restore_disabled = system_restore_disabled
        self.task_manager_disabled = task_manager_disabled
        self.uac_disabled = uac_disabled
        self.warning_on_zone_crossing_disabled = warning_on_zone_crossing_disabled
        self.warning_post_redirection_disabled = warning_post_redirection_disabled
        self.manufacturer = manufacturer
        self.model = model
        self.network_adapter_promisc_mode = network_adapter_promisc_mode
        self.operating_system = operating_system
        self.processor_architecture = processor_architecture
        self.processor_count = processor_count
        self.platform = platform
        self.processor_is_32_bits = processor_is_32_bits
        self.processor_is_64 = processor_is_64
        self.processor_name = processor_name
        self.scanning = scanning
        self.scan_start_time = scan_start_time
        self.serial = serial
        self.timezone = timezone
        self.total_physical_memory = total_physical_memory
        self.https_fallback_mode = https_fallback_mode
        self.blocking_active = blocking_active
        self.roaming_agents_relay_system_active = roaming_agents_relay_system_active
        self.user_id = user_id
        self.windows_directory = windows_directory
        self.netwitness_investigate = netwitness_investigate
        self.containment_status = containment_status

    def to_enrichment_data(self, prefix=None):
        new_dict = {
            "DriverErrorCode": self.driver_error_code,
            "ServicePackOS": self.servicepack_os,
            "MachineStatus": self.machine_status,
            "Type": self.machine_type,
            "VersionInfo": self.version_info,
            "UserName": self.username,
            "OrganizationUnit": self.organization_unit,
            "LocalIP": self.local_ip,
            "NetworkSegment": self.network_segment,
            "Gateway": self.gateway,
            "RemoteIP": self.remote_ip,
            "Group": self.group,
            "AdminStatus": self.admin_status,
            "KernelDebuggerDetected": self.kernel_debugger_detected,
            "EarlyStart": self.early_start,
            "NotifyShutdownModule": self.notify_shutdown_module,
            "LoadedModuleModule": self.loaded_module_module,
            "NotifyRoutineModule": self.notify_routine_module,
            "UnloadedDriverModule": self.unloaded_driver_module,
            "ErrorLogModule": self.error_log_module,
            "LowLevelReaderModule": self.low_level_reader_module,
            "ProcessModule": self.process_module,
            "WorkerThreadModule": self.worker_thread_module,
            "WindowsHooksModule": self.windows_hooks_module,
            "DebuggerAttachedToProcess": self.debugger_attached_to_process,
            "ProcessMonitorModule": self.process_monitor_module,
            "ThreadMonitorModule": self.thread_monitor_module,
            "ObjectMonitorModule": self.object_monitor_module,
            "ImageMonitorModule": self.image_monitor_module,
            "DriverMonitorModule": self.driver_monitor_module,
            "TdiMonitorModule": self.idi_monitor_module,
            "TrackingModule": self.tracking_module,
            "TrackingRegistryMonitor": self.tracking_registry_monitor,
            "TrackingObjectMonitor": self.tracking_object_monitor,
            "TrackingFileMonitor": self.tracking_file_monitor,
            "TrackingRemoteThreadMonitor": self.tracking_remote_thread_monitor,
            "TrackingCreateProcessMonitor": self.tracking_create_process_monitor,
            "TrackingHardLinkMonitor": self.tracking_hard_link_monitor,
            "TrackingFileBlockMonitor": self.tracking_file_block_monitor,
            "TrackingNetworkMonitor": self.tracking_network_monitor,
            "ECATServerName": self.ecat_server_name,
            "Online": self.online,
            "IIOCScore": self.iioc_score,
            "ChassisType": self.chassis_type,
            "ContainmentSupported": self.containment_supported,
            "AgentID": self.agent_id,
            "BIOS": self.bios,
            "OSBuildNumber": self.os_build_number,
            "Comment": self.comment,
            "ConnectionTime": self.connection_time,
            "Language": self.language,
            "DNS": self.dns,
            "DomainRole": self.domain_role,
            "ECATServiceCompileTime": self.ecat_service_compile_time,
            "ECATPackageTime": self.ecat_package_time,
            "StartTime": self.start_time,
            "ECATDriverCompileTime": self.ecat_driver_compile_time,
            "DomainName": self.domain_name,
            "Idle": self.idle,
            "IncludedinMonitoring": self.include_in_monitoring,
            "IncludedinScanSchedule": self.include_in_schedule,
            "InstallationFailed": self.installation_failed,
            "InstallTime": self.install_time,
            "IIOCLevel0": self.iioc_level0,
            "IIOCLevel1": self.iioc_level1,
            "IIOCLevel2": self.iioc_level2,
            "IIOCLevel3": self.iioc_level3,
            "Country": self.country,
            "BootTime": self.boot_time,
            "LastScan": self.last_scan,
            "LastSeen": self.last_seen,
            "MAC": self.mac,
            "MachineID": self.machine_id,
            "MachineName": self.machine_name,
            "AllowAccessDataSourceDomain": self.allow_access_data_source_domain,
            "AllowDisplayMixedContent": self.allow_display_mixed_content,
            "AntiVirusDisabled": self.antivirus_disabled,
            "BadCertificateWarningDisabled": self.bad_certificate_warning_disabled,
            "CookiesCleanupDisabled": self.cookies_cleanup_disabled,
            "CrosssiteScriptFilterDisabled": self.crossite_script_filter_disabled,
            "FirewallDisabled": self.firewall_disabled,
            "IEDepDisabled": self.iedep_disabled,
            "IEEnhancedSecurityDisabled": self.ieenhanced_security_disabled,
            "IntranetZoneNotificationDisabled": self.intranet_zone_notification_disabled,
            "LUADisabled": self.lua_disabled,
            "NoAntivirusNotificationDisabled": self.no_antivirus_notification_disabled,
            "NoFirewallNotificationDisabled": self.no_firewall_notification_disabled,
            "NoUACNotificationDisabled": self.no_uac_notification_disabled,
            "NoWindowsUpdateDisabled": self.no_windows_update_disabled,
            "RegistryToolsDisabled": self.registry_tools_disabled,
            "SmartscreenFilterDisabled": self.smart_screen_filter_disabled,
            "SystemRestoreDisabled": self.system_restore_disabled,
            "TaskManagerDisabled": self.task_manager_disabled,
            "UACDisabled": self.uac_disabled,
            "WarningOnZoneCrossingDisabled": self.warning_on_zone_crossing_disabled,
            "WarningPostRedirectionDisabled": self.warning_post_redirection_disabled,
            "Manufacturer": self.manufacturer,
            "Model": self.model,
            "NetworkAdapterPromiscMode": self.network_adapter_promisc_mode,
            "OperatingSystem": self.operating_system,
            "ProcessorArchitecture": self.processor_architecture,
            "ProcessorCount": self.processor_count,
            "Platform": self.platform,
            "ProcessorIs32bits": self.processor_is_32_bits,
            "Processoris64": self.processor_is_64,
            "ProcessorName": self.processor_name,
            "Scanning": self.scanning,
            "ScanStartTime": self.scan_start_time,
            "Serial": self.serial,
            "TimeZone": self.timezone,
            "TotalPhysicalMemory": self.total_physical_memory,
            "HTTPSFallbackMode": self.https_fallback_mode,
            "BlockingActive": self.blocking_active,
            "RoamingAgentsRelaySystemActive": self.roaming_agents_relay_system_active,
            "UserID": self.user_id,
            "WindowsDirectory": self.windows_directory,
            "NetWitnessInvestigate": self.netwitness_investigate,
            "ContainmentStatus": self.containment_status,
        }
        data = dict_to_flat(new_dict)
        return add_prefix_to_dict(data, prefix) if prefix else data
