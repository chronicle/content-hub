from __future__ import annotations

from datetime import datetime

from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.extraction import extract_action_param

from ..core.auth import build_auth_params
from ..core.base_action import SignalSciencesAction


class AddIpToBlockListAction(SignalSciencesAction):
    def __init__(self):
        super().__init__("SignalSciences - Add IP to Block List")

    def _perform_action(self, _=None) -> None:
        site_name = extract_action_param(
            self.soar_action,
            param_name="Site Name",
            is_mandatory=True
        )
        note = extract_action_param(
            self.soar_action,
            param_name="Note",
            is_mandatory=True
        )
        ip_param = extract_action_param(
            self.soar_action,
            param_name="IP Address",
            is_mandatory=False
        )
        
        ips = []
        # 1. Get from parameter
        if ip_param:
            ips.extend([ip.strip() for ip in ip_param.split(",") if ip.strip()])
            
        # 2. Get from entities
        for entity in self.soar_action.target_entities:
            if entity.entity_type == EntityTypesEnum.ADDRESS:
                ips.append(entity.additional_properties.get("ipAddress") or entity.identifier)

        ips = list(set(ips))

        if not ips:
            self.output_message = "No IP addresses found to add."
            self.result_value = False
            return

        success_ips = []
        failed_ips = []
        
        for ip in ips:
            try:
                payload = {
                    "source": ip,
                    "note": note
                }
                self.api_client.add_blocklist_item(site_name, payload)
                success_ips.append(ip)
            except Exception as e:
                self.logger.error(f"Failed to add IP {ip} to blocklist for site {site_name}: {e}")
                failed_ips.append(ip)

        try:
            auth_params = build_auth_params(self.soar_action)
            email = auth_params.email
        except Exception:
            email = ""

        result_json = {
            "added_entities": success_ips,
            "failed_entities": failed_ips,
            "site_name": site_name,
            "created_by": email,
            "note": note,
            "created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        }
        self.soar_action.result.add_result_json(result_json)

        if success_ips:
            ips_str = ", ".join(success_ips)
            self.output_message = (
                f"Successfully added IPs to block list for "
                f"site {site_name}: {ips_str}"
            )
            if failed_ips:
                self.output_message += f". Failed for: {', '.join(failed_ips)}"
            self.result_value = True
        else:
            self.output_message = f"Failed to add all IPs ({', '.join(ips)}) to block list."
            self.result_value = False


def main():
    AddIpToBlockListAction().run()


if __name__ == "__main__":
    main()
