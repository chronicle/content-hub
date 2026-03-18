from __future__ import annotations

from TIPCommon.extraction import extract_action_param

from ..core.base_action import SignalSciencesAction


class ListSitesAction(SignalSciencesAction):
    def __init__(self):
        super().__init__("SignalSciences - List Sites")

    def _perform_action(self, _=None) -> None:
        limit = extract_action_param(
            self.soar_action,
            param_name="Limit",
            default_value=100,
            input_type=int
        )
        
        sites = self.api_client.list_sites(limit=limit)
        
        if sites:
            self.output_message = f"Successfully found {len(sites)} sites."
            self.soar_action.result.add_result_json(sites)
            self.result_value = True
        else:
            self.output_message = "No sites found."
            self.result_value = False


def main():
    ListSitesAction().run()


if __name__ == "__main__":
    main()
