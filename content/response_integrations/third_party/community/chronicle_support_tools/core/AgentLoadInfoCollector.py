from __future__ import annotations

from .utils import CommonUtils

# CALI


class AgentLoadInfoCollector:
    _integration_name = None
    _siemplify = None

    def __init__(self, integration_name, siemplify):
        self._integration_name = integration_name
        self._siemplify = siemplify

    def collect_cpu_load(self):
        output = []
        output.append(CommonUtils.collect_command_output(["lscpu"]))
        output.append("Uptime and Load average")
        output.append(CommonUtils.collect_command_output(["uptime"]))
        output.append("Memory Information")
        output.append(CommonUtils.collect_command_output(["free", "-h"]))
        output.append("siemplify_agent Environment Variables")
        output.append(
            "\n".join(
                line
                for line in CommonUtils.collect_command_output(["env"]).splitlines()
                if all(
                    pattern not in line.lower()
                    for pattern in ["token", "key", "hostname"]
                )
            ),
        )
        return "\n".join(output)

    def log_collected_info(self):
        self._siemplify.LOGGER.info(
            "============= Collecting Agent Load Information (CALI) =============",
        )

        self._siemplify.LOGGER.info(str(self.collect_cpu_load()))

        self._siemplify.LOGGER.info(
            "============= Finish Collecting Agent Load Information (CALI) =============",
        )


class CollectFileInformation:
    _integration_name = None
    _siemplify = None

    def __init__(self, integration_name, siemplify):
        self._integration_name = integration_name
        self._siemplify = siemplify

    def collect_file_info(self):
        output = []
        output.append("")
        output.append("File Information Agent Process working directory")
        output.append(
            CommonUtils.collect_command_output(["ls", "-lart", "/opt/SiemplifyAgent"]),
        )
        return "\n".join(output)

    def log_collected_info(self):
        self._siemplify.LOGGER.info(
            "============= Collecting File Information (CFI) =============",
        )

        self._siemplify.LOGGER.info(str(self.collect_file_info()))

        self._siemplify.LOGGER.info(
            "============= Finish Collecting File Information (CFI) =============",
        )
