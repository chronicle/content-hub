from __future__ import annotations

from SiemplifyDataModel import EntityTypes
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param

from ..core.base_action import SignalSciencesAction
from ..core.datamodels import AllowListItem

SCRIPT_NAME = "Add IP to Allow List"


class AddIpToAllowListAction(SignalSciencesAction):
    def __init__(self):
        super().__init__(SCRIPT_NAME)
        self.successful_ips = []
        self.failed_ips = []
        self.json_results = []

    def _extract_action_parameters(self) -> None:
        self.site_name = extract_action_param(self.soar_action, "Site Name", is_mandatory=True)
        self.ip_addresses_param = extract_action_param(
            self.soar_action, "IP Address", default_value=""
        )
        self.note = extract_action_param(self.soar_action, "Note", is_mandatory=True)
        self.logger.info(f"Extracted Note: {self.note}")

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
            allowlists = self.api_client.get_allowlists(site_name=self.site_name)
        except Exception as e:
            # Handle "Site not found" specifically if possible
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

        existing_ips = {item["source"]: item for item in allowlists}
        first_item = None

        for ip_address in target_ips:
            self.logger.info(f"Processing IP: {ip_address}")
            if not self.is_valid_ip(ip_address):
                self.logger.warn(f"IP {ip_address} is not a valid IPv4 or IPv6 address. Skipping.")
                self.failed_ips.append(ip_address)
                continue

            if ip_address in existing_ips:
                self.logger.info(
                    f"IP {ip_address} already exists in the allow list. Using existing data."
                )
                item = AllowListItem(existing_ips[ip_address])
                if not first_item:
                    first_item = item
                self.successful_ips.append(ip_address)
                continue

            try:
                raw_data = self.api_client.add_ip_to_allowlist(
                    site_name=self.site_name, ip_address=ip_address, note=self.note
                )
                item = AllowListItem(raw_data)
                if not first_item:
                    first_item = item
                self.successful_ips.append(ip_address)
            except Exception as e:
                self.logger.error(f"Failed to add IP {ip_address}: {e}")
                self.failed_ips.append(ip_address)

        # Construct Generic JsonResult
        self.json_results = {
            "added_entities": self.successful_ips,
            "failed_entities": self.failed_ips,
            "site_name": self.site_name,
            "created_by": getattr(first_item, "created_by", "") if first_item else "",
            "note": getattr(first_item, "note", self.note) if first_item else self.note,
            "created": getattr(first_item, "created", "") if first_item else "",
        }

    def _finalize_action_on_success(self) -> None:
        if self.execution_state == ExecutionState.FAILED or (
            not self.successful_ips and not self.failed_ips
        ):
            return

        if self.successful_ips:
            self.output_message = (
                f"Successfully added the following IPs to the Allow List for "
                f"site {self.site_name} in Signal Sciences:\n{', '.join(self.successful_ips)}\n"
            )

        if self.failed_ips:
            error_msg = (
                f"Failed to add the following IPs to the Allow List for site "
                f"{self.site_name} in Signal Sciences:\n{', '.join(self.failed_ips)}\n"
            )
            if self.output_message:
                self.output_message += f"\n{error_msg}"
            else:
                self.output_message = error_msg

            self.result_value = False
        else:
            self.result_value = True


def main():
    AddIpToAllowListAction().run()


if __name__ == "__main__":
    main()
