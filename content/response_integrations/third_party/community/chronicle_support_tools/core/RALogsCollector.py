from __future__ import annotations

import json
import traceback

from .utils import CommonUtils, DataFilter

# CASI


class RALogsCollector:
    _integration_name = None
    _siemplify = None

    def __init__(self, integration_name, siemplify):
        self._integration_name = integration_name
        self._siemplify = siemplify
        self.printInit()

    def flatten_json(self, input_json):
        js = json.loads(input_json)
        flattened_output = []

        integration_details = []

        for x in js:
            if "integrations" not in x:
                element = str(x) + " : " + str(js[x])
                flattened_output.append(DataFilter.truncateSensitiveData(element))
            if "integrations" in x:
                try:
                    integrations_list = json.loads(js[x])
                    for elems in integrations_list:
                        integration_details.append(
                            "Integration :"
                            + elems["name"]
                            + " , Version :"
                            + elems["version"],
                        )
                except Exception:
                    self._siemplify.LOGGER.info(
                        "Unable to fetch Integration Details : "
                        + str(traceback.format_exc()),
                    )
                    self._siemplify.LOGGER.info(
                        "More details : " + str(js["integrations"]),
                    )

        return flattened_output + integration_details

    def log_collected_info(self):
        try:
            output = CommonUtils.collect_command_output(
                ["cat", "/opt/SiemplifyAgent/Resources/agent_status.json"],
            )
            agentDetails = self.flatten_json(output)

            self._siemplify.LOGGER.info(
                "============= Collecting Agent Information (CASI) =============",
            )
            for x in agentDetails:
                self._siemplify.LOGGER.info(x)

            import ssl

            self._siemplify.LOGGER.info(str(ssl.OPENSSL_VERSION))
            time = CommonUtils.collect_command_output(["date"])

            self._siemplify.LOGGER.info("Agent Date/Time + TZ : " + time)
            self._siemplify.LOGGER.info(
                "============= Finished Collecting Agent Information (CASI) =============",
            )

        except Exception as e:
            self._siemplify.LOGGER.info("Unable to fetch Agent Details : " + str(e))
            self._siemplify.LOGGER.info(
                "Unable to fetch Agent Details : " + str(traceback.format_exc()),
            )

    def printInit(self):
        self._siemplify.LOGGER.info(
            "============= Init Remote Agent Logs Collector Chronicle Support Tools =============",
        )
