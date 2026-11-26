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
from .datamodels import *


class RSAParser:

    def build_domains_object(self, raw_json):

        domains = raw_json.get("Domains")
        return Domains(raw_data=raw_json, domains=domains)

    def build_ips_object(self, raw_json):

        ips = raw_json.get("Ips")
        return IPs(raw_data=raw_json, ips=ips)

    def build_iocs_object(self, raw_json):

        return IOCS(
            raw_data=raw_json,
            alert_table=raw_json.get("Alertable"),
            evaluation_date=raw_json.get("EvaluationDate"),
            ioc_context=raw_json.get("IOCContext"),
            ioc_triggered_on_machine=raw_json.get("IOCTriggeredOnMachine"),
            bias_status=raw_json.get("BiasStatus"),
            active=raw_json.get("Active"),
            description=raw_json.get("Description"),
            ioc_type=raw_json.get("Type"),
            ioc_level=raw_json.get("IOCLevel"),
            last_executed=raw_json.get("LastExecuted"),
            name=raw_json.get("Name"),
            priority=raw_json.get("Priority"),
            query=raw_json.get("Query"),
            machine_count=raw_json.get("MachineCount"),
            module_count=raw_json.get("ModuleCount"),
        )

    def build_ioclevel_object(self, raw_json):

        return IOCLevel(
            raw_data=raw_json,
            active=raw_json.get("iocQuery", {}).get("Active"),
            alert_table=raw_json.get("iocQuery", {}).get("Alertable"),
            blacklisted_count=raw_json.get("iocQuery", {}).get("BlacklistedCount"),
            graylisted_count=raw_json.get("iocQuery", {}).get("GraylistedCount"),
            description=raw_json.get("iocQuery", {}).get("Description"),
            error_message=raw_json.get("iocQuery", {}).get("ErrorMessage"),
            evaluation_machine_count=raw_json.get("iocQuery", {}).get(
                "EvaluationMachineCount"
            ),
            ioc_type=raw_json.get("iocQuery", {}).get("Type"),
            ioc_level=raw_json.get("iocQuery", {}).get("IOCLevel"),
            last_evaluation_duration=raw_json.get("iocQuery", {}).get(
                "LastEvaluationDuration"
            ),
            last_execution_duration=raw_json.get("iocQuery", {}).get(
                "LastExecutionDuration"
            ),
            last_executed=raw_json.get("iocQuery", {}).get("LastExecuted"),
            machine_count=raw_json.get("iocQuery", {}).get("MachineCount"),
            module_count=raw_json.get("iocQuery", {}).get("ModuleCount"),
            name=raw_json.get("iocQuery", {}).get("Name"),
            persistent=raw_json.get("iocQuery", {}).get("Persistent"),
            priority=raw_json.get("iocQuery", {}).get("Priority"),
            query=raw_json.get("iocQuery", {}).get("Query"),
            user_defined=raw_json.get("iocQuery", {}).get("UserDefined"),
            whitelisted_count=raw_json.get("iocQuery", {}).get("WhitelistedCount"),
        )

    def build_iocs_object_json(self, iocs_details_list):

        iocs_details_list_json = [
            iocs_detail.to_json() for iocs_detail in iocs_details_list
        ]
        iocs_details_json = {"Iocs": iocs_details_list_json}

        return iocs_details_json

    def build_machine_object(self, raw_json):

        return Machine(
            raw_data=raw_json,
            driver_error_code=raw_json.get("Machine", {}).get("DriverErrorCode"),
            servicepack_os=raw_json.get("Machine", {}).get("ServicePackOS"),
            machine_status=raw_json.get("Machine", {}).get("MachineStatus"),
            machine_type=raw_json.get("Machine", {}).get("Type"),
            version_info=raw_json.get("Machine", {}).get("VersionInfo"),
            username=raw_json.get("Machine", {}).get("UserName"),
            organization_unit=raw_json.get("Machine", {}).get("OrganizationUnit"),
            local_ip=raw_json.get("Machine", {}).get("LocalIP"),
            network_segment=raw_json.get("Machine", {}).get("NetworkSegment"),
            gateway=raw_json.get("Machine", {}).get("Gateway"),
            remote_ip=raw_json.get("Machine", {}).get("RemoteIP"),
            group=raw_json.get("Machine", {}).get("Group"),
            admin_status=raw_json.get("Machine", {}).get("AdminStatus"),
            kernel_debugger_detected=raw_json.get("Machine", {}).get(
                "KernelDebuggerDetected"
            ),
            early_start=raw_json.get("Machine", {}).get("EarlyStart"),
            notify_shutdown_module=raw_json.get("Machine", {}).get(
                "NotifyShutdownModule"
            ),
            loaded_module_module=raw_json.get("Machine", {}).get("LoadedModuleModule"),
            notify_routine_module=raw_json.get("Machine", {}).get(
                "NotifyRoutineModule"
            ),
            unloaded_driver_module=raw_json.get("Machine", {}).get(
                "UnloadedDriverModule"
            ),
            error_log_module=raw_json.get("Machine", {}).get("ErrorLogModule"),
            low_level_reader_module=raw_json.get("Machine", {}).get(
                "LowLevelReaderModule"
            ),
            process_module=raw_json.get("Machine", {}).get("ProcessModule"),
            worker_thread_module=raw_json.get("Machine", {}).get("WorkerThreadModule"),
            windows_hooks_module=raw_json.get("Machine", {}).get("WindowsHooksModule"),
            debugger_attached_to_process=raw_json.get("Machine", {}).get(
                "DebuggerAttachedToProcess"
            ),
            process_monitor_module=raw_json.get("Machine", {}).get(
                "ProcessMonitorModule"
            ),
            thread_monitor_module=raw_json.get("Machine", {}).get(
                "ThreadMonitorModule"
            ),
            object_monitor_module=raw_json.get("Machine", {}).get(
                "ObjectMonitorModule"
            ),
            image_monitor_module=raw_json.get("Machine", {}).get("ImageMonitorModule"),
            driver_monitor_module=raw_json.get("Machine", {}).get(
                "DriverMonitorModule"
            ),
            idi_monitor_module=raw_json.get("Machine", {}).get("TdiMonitorModule"),
            tracking_module=raw_json.get("Machine", {}).get("TrackingModule"),
            tracking_registry_monitor=raw_json.get("Machine", {}).get(
                "TrackingRegistryMonitor"
            ),
            tracking_object_monitor=raw_json.get("Machine", {}).get(
                "TrackingObjectMonitor"
            ),
            tracking_file_monitor=raw_json.get("Machine", {}).get(
                "TrackingFileMonitor"
            ),
            tracking_remote_thread_monitor=raw_json.get("Machine", {}).get(
                "TrackingRemoteThreadMonitor"
            ),
            tracking_create_process_monitor=raw_json.get("Machine", {}).get(
                "TrackingCreateProcessMonitor"
            ),
            tracking_hard_link_monitor=raw_json.get("Machine", {}).get(
                "TrackingHardLinkMonitor"
            ),
            tracking_file_block_monitor=raw_json.get("Machine", {}).get(
                "TrackingFileBlockMonitor"
            ),
            tracking_network_monitor=raw_json.get("Machine", {}).get(
                "TrackingNetworkMonitor"
            ),
            ecat_server_name=raw_json.get("Machine", {}).get("ECATServerName"),
            online=raw_json.get("Machine", {}).get("Online"),
            iioc_score=raw_json.get("Machine", {}).get("IIOCScore"),
            chassis_type=raw_json.get("Machine", {}).get("ChassisType"),
            containment_supported=raw_json.get("Machine", {}).get(
                "ContainmentSupported"
            ),
            agent_id=raw_json.get("Machine", {}).get("AgentID"),
            bios=raw_json.get("Machine", {}).get("BIOS"),
            os_build_number=raw_json.get("Machine", {}).get("OSBuildNumber"),
            comment=raw_json.get("Machine", {}).get("Comment"),
            connection_time=raw_json.get("Machine", {}).get("ConnectionTime"),
            language=raw_json.get("Machine", {}).get("Language"),
            dns=raw_json.get("Machine", {}).get("DNS"),
            domain_role=raw_json.get("Machine", {}).get("DomainRole"),
            ecat_service_compile_time=raw_json.get("Machine", {}).get(
                "ECATServiceCompileTime"
            ),
            ecat_package_time=raw_json.get("Machine", {}).get("ECATPackageTime"),
            start_time=raw_json.get("Machine", {}).get("StartTime"),
            ecat_driver_compile_time=raw_json.get("Machine", {}).get(
                "ECATDriverCompileTime"
            ),
            domain_name=raw_json.get("Machine", {}).get("DomainName"),
            idle=raw_json.get("Machine", {}).get("Idle"),
            include_in_monitoring=raw_json.get("Machine", {}).get(
                "IncludedinMonitoring"
            ),
            include_in_schedule=raw_json.get("Machine", {}).get(
                "IncludedinScanSchedule"
            ),
            installation_failed=raw_json.get("Machine", {}).get("InstallationFailed"),
            install_time=raw_json.get("Machine", {}).get("InstallTime"),
            iioc_level0=raw_json.get("Machine", {}).get("IIOCLevel0"),
            iioc_level1=raw_json.get("Machine", {}).get("IIOCLevel1"),
            iioc_level2=raw_json.get("Machine", {}).get("IIOCLevel2"),
            iioc_level3=raw_json.get("Machine", {}).get("IIOCLevel3"),
            country=raw_json.get("Machine", {}).get("Country"),
            boot_time=raw_json.get("Machine", {}).get("BootTime"),
            last_scan=raw_json.get("Machine", {}).get("LastScan"),
            last_seen=raw_json.get("Machine", {}).get("LastSeen"),
            mac=raw_json.get("Machine", {}).get("MAC"),
            machine_id=raw_json.get("Machine", {}).get("MachineID"),
            machine_name=raw_json.get("Machine", {}).get("MachineName"),
            allow_access_data_source_domain=raw_json.get("Machine", {}).get(
                "AllowAccessDataSourceDomain"
            ),
            allow_display_mixed_content=raw_json.get("Machine", {}).get(
                "AllowDisplayMixedContent"
            ),
            antivirus_disabled=raw_json.get("Machine", {}).get("AntiVirusDisabled"),
            bad_certificate_warning_disabled=raw_json.get("Machine", {}).get(
                "BadCertificateWarningDisabled"
            ),
            cookies_cleanup_disabled=raw_json.get("Machine", {}).get(
                "CookiesCleanupDisabled"
            ),
            crossite_script_filter_disabled=raw_json.get("Machine", {}).get(
                "CrosssiteScriptFilterDisabled"
            ),
            firewall_disabled=raw_json.get("Machine", {}).get("FirewallDisabled"),
            iedep_disabled=raw_json.get("Machine", {}).get("IEDepDisabled"),
            ieenhanced_security_disabled=raw_json.get("Machine", {}).get(
                "IEEnhancedSecurityDisabled"
            ),
            intranet_zone_notification_disabled=raw_json.get("Machine", {}).get(
                "IntranetZoneNotificationDisabled"
            ),
            lua_disabled=raw_json.get("Machine", {}).get("LUADisabled"),
            no_antivirus_notification_disabled=raw_json.get("Machine", {}).get(
                "NoAntivirusNotificationDisabled"
            ),
            no_firewall_notification_disabled=raw_json.get("Machine", {}).get(
                "NoFirewallNotificationDisabled"
            ),
            no_uac_notification_disabled=raw_json.get("Machine", {}).get(
                "NoUACNotificationDisabled"
            ),
            no_windows_update_disabled=raw_json.get("Machine", {}).get(
                "NoWindowsUpdateDisabled"
            ),
            registry_tools_disabled=raw_json.get("Machine", {}).get(
                "RegistryToolsDisabled"
            ),
            smart_screen_filter_disabled=raw_json.get("Machine", {}).get(
                "SmartscreenFilterDisabled"
            ),
            system_restore_disabled=raw_json.get("Machine", {}).get(
                "SystemRestoreDisabled"
            ),
            task_manager_disabled=raw_json.get("Machine", {}).get(
                "TaskManagerDisabled"
            ),
            uac_disabled=raw_json.get("Machine", {}).get("UACDisabled"),
            warning_on_zone_crossing_disabled=raw_json.get("Machine", {}).get(
                "WarningOnZoneCrossingDisabled"
            ),
            warning_post_redirection_disabled=raw_json.get("Machine", {}).get(
                "WarningPostRedirectionDisabled"
            ),
            manufacturer=raw_json.get("Machine", {}).get("Manufacturer"),
            model=raw_json.get("Machine", {}).get("Model"),
            network_adapter_promisc_mode=raw_json.get("Machine", {}).get(
                "NetworkAdapterPromiscMode"
            ),
            operating_system=raw_json.get("Machine", {}).get("OperatingSystem"),
            processor_architecture=raw_json.get("Machine", {}).get(
                "ProcessorArchitecture"
            ),
            processor_count=raw_json.get("Machine", {}).get("ProcessorCount"),
            platform=raw_json.get("Machine", {}).get("Platform"),
            processor_is_32_bits=raw_json.get("Machine", {}).get("ProcessorIs32bits"),
            processor_is_64=raw_json.get("Machine", {}).get("Processoris64"),
            processor_name=raw_json.get("Machine", {}).get("ProcessorName"),
            scanning=raw_json.get("Machine", {}).get("Scanning"),
            scan_start_time=raw_json.get("Machine", {}).get("ScanStartTime"),
            serial=raw_json.get("Machine", {}).get("Serial"),
            timezone=raw_json.get("Machine", {}).get("TimeZone"),
            total_physical_memory=raw_json.get("Machine", {}).get(
                "TotalPhysicalMemory"
            ),
            https_fallback_mode=raw_json.get("Machine", {}).get("HTTPSFallbackMode"),
            blocking_active=raw_json.get("Machine", {}).get("BlockingActive"),
            roaming_agents_relay_system_active=raw_json.get("Machine", {}).get(
                "RoamingAgentsRelaySystemActive"
            ),
            user_id=raw_json.get("Machine", {}).get("UserID"),
            windows_directory=raw_json.get("Machine", {}).get("WindowsDirectory"),
            netwitness_investigate=raw_json.get("Machine", {}).get(
                "NetWitnessInvestigate"
            ),
            containment_status=raw_json.get("Machine", {}).get("ContainmentStatus"),
        )
