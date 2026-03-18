from __future__ import annotations

from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.extraction import extract_action_param

from ..core.base_action import SignalSciencesAction


class RemoveIpFromBlockListAction(SignalSciencesAction):
    def __init__(self):
        super().__init__("SignalSciences - Remove IP from Block List")

    def _perform_action(self, _=None) -> None:
        site_name = extract_action_param(
            self.soar_action,
            param_name="Site Name",
            is_mandatory=True
        )
        ip_param = extract_action_param(
            self.soar_action,
            param_name="IP Address",
            is_mandatory=False
        )
        
        ips = []
        if ip_param:
            ips.extend([ip.strip() for ip in ip_param.split(",") if ip.strip()])
            
        for entity in self.soar_action.target_entities:
            if entity.entity_type == EntityTypesEnum.ADDRESS:
                ips.append(entity.additional_properties.get("ipAddress") or entity.identifier)

        ips = list(set(ips))

        if not ips:
            self.output_message = "No IP addresses found to remove."
            self.result_value = False
            return

        try:
            current_list = self.api_client.get_blacklist(site_name)
        except Exception as e:
            self.output_message = f"Failed to fetch blocklist for site {site_name}: {e}"
            self.result_value = False
            return

        ip_to_id = {}
        for item in current_list:
            ip = item.get("ip") or item.get("source")
            if ip:
                ip_to_id[ip] = item.get("id")

        success_ips = []
        failed_ips = []
        not_found_ips = []

        for ip in ips:
            if ip not in ip_to_id:
                not_found_ips.append(ip)
                continue

            try:
                item_id = ip_to_id[ip]
                self.api_client.delete_blacklist_item(site_name, item_id)
                success_ips.append(ip)
            except Exception as e:
                self.logger.error(f"Failed to remove IP {ip} from blocklist for site {site_name}: {e}")
                failed_ips.append(ip)

        messages = []
        if success_ips:
            messages.append(f"Successfully removed: {', '.join(success_ips)}")
        if not_found_ips:
            messages.append(f"Not found in list: {', '.join(not_found_ips)}")
        if failed_ips:
            messages.append(f"Failed to remove: {', '.join(failed_ips)}")

        self.output_message = ". ".join(messages)
        self.result_value = len(success_ips) > 0 or len(not_found_ips) == len(ips)


def main():
    RemoveIpFromBlockListAction().run()


if __name__ == "__main__":
    main()
