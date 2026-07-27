from __future__ import annotations

from SiemplifyDataModel import EntityTypes
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param

from ..core.base_action import SignalSciencesAction

SCRIPT_NAME = "Remove IP from Block List"


class RemoveIpFromBlockListAction(SignalSciencesAction):
    def __init__(self):
        super().__init__(SCRIPT_NAME)
        self.successful_ips = []
        self.failed_ips = []

    def _extract_action_parameters(self) -> None:
        self.site_name = extract_action_param(self.soar_action, "Site Name", is_mandatory=True)
        self.ip_addresses_param = extract_action_param(
            self.soar_action, "IP Address", default_value=""
        )

    def _perform_action(self, _=None) -> None:
        target_ips = []
        if self.ip_addresses_param:
            target_ips.extend([
                ip.strip() for ip in self.ip_addresses_param.split(",") if ip.strip()
            ])

        suitable_entities = [
            entity.identifier
            for entity in self.soar_action.target_entities
            if entity.entity_type == EntityTypes.ADDRESS
        ]
        target_ips.extend(suitable_entities)
        target_ips = list(dict.fromkeys(target_ips))

        if not target_ips:
            self.output_message = (
                "No IP addresses were provided as parameters or found as entities."
            )
            self.result_value = False
            return

        try:
            blocklists = self.api_client.get_blocklists(site_name=self.site_name)
        except Exception as e:
            error_message = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    res_json = e.response.json()
                    if res_json.get("message") == "Site not found":
                        error_message = f"Site {self.site_name} not found."
                    else:
                        error_message = res_json.get("message", error_message)
                except ValueError:
                    pass

            self.output_message = (
                f'Error executing action: "{SCRIPT_NAME}". Reason: {error_message}'
            )
            self.logger.error(self.output_message)
            self.result_value = False
            self.execution_state = ExecutionState.FAILED
            return

        for ip_address in target_ips:
            self.logger.info(f"Processing IP: {ip_address}")
            if not self.is_valid_ip(ip_address):
                self.logger.warn(f"IP {ip_address} is not a valid IPv4 or IPv6 address. Skipping.")
                self.failed_ips.append(ip_address)
                continue

            try:
                matching_items = [item for item in blocklists if item["source"] == ip_address]
                if not matching_items:
                    self.logger.info(
                        f"IP {ip_address} not found in the block list. "
                        "Treating as successfully removed."
                    )
                    self.successful_ips.append(ip_address)
                    continue

                for item in matching_items:
                    self.api_client.remove_ip_from_blocklist(
                        site_name=self.site_name, item_id=item["id"]
                    )
                self.successful_ips.append(ip_address)
            except Exception as e:
                self.logger.error(f"Failed to remove IP {ip_address}: {e}")
                self.failed_ips.append(ip_address)

    def _finalize_action_on_success(self) -> None:
        if self.execution_state == ExecutionState.FAILED or (
            not self.successful_ips and not self.failed_ips
        ):
            return

        if self.successful_ips:
            self.output_message = (
                f"Successfully removed the following IPs from the Block List for "
                f"site {self.site_name} in Signal Sciences:\n{', '.join(self.successful_ips)}\n"
            )

        if self.failed_ips:
            error_msg = (
                f"Failed to remove the following IPs from the Block List for "
                f"site {self.site_name} in Signal Sciences:\n{', '.join(self.failed_ips)}\n"
            )
            if self.output_message:
                self.output_message += f"\n{error_msg}"
            else:
                self.output_message = error_msg

            self.result_value = False
        else:
            self.result_value = True


def main():
    RemoveIpFromBlockListAction().run()


if __name__ == "__main__":
    main()
