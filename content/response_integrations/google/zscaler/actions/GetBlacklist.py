from __future__ import annotations

from TIPCommon.transformation import construct_csv

from zscaler.core.base_action import ZscalerBaseAction
from zscaler.core.constants import GET_BLACKLIST_SCRIPT_NAME


class GetBlacklistAction(ZscalerBaseAction):
    def __init__(self) -> None:
        super().__init__(GET_BLACKLIST_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: str = ""

    def _perform_action(self, _=None) -> None:
        """Perform the action."""
        blacklist_dict = self.api_client.get_blacklist_items()
        blacklist = blacklist_dict.get("blacklistUrls")

        if blacklist:
            self.output_message = f"Found {len(blacklist)} Blocked Malicious URLs"
            self.result_value = ", ".join(blacklist)

            csv_output = construct_csv([{"Blacklisted URL": url} for url in blacklist])
            self.soar_action.result.add_data_table("Blacklist Urls", csv_output)
            self.soar_action.result.add_result_json(blacklist_dict)
        else:
            self.output_message = "Found 0 Blocked Malicious URLs"
            self.result_value = " "
            self.soar_action.result.add_result_json({})


def main() -> None:
    GetBlacklistAction().run()


if __name__ == "__main__":
    main()
