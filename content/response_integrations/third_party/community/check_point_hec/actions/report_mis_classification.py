from ..core.base_action import BaseAction
from ..core.constants import REPORT_MIS_CLASSIFICATION_SCRIPT_NAME, MIS_CLASSIFICATION_OPTIONS, \
    MIS_CLASSIFICATION_CONFIDENCE

SUCCESS_MESSAGE: str = "Successfully Reported Mis Classification!"
ERROR_MESSAGE: str = "Failed Reporting Mis Classification!"


class ReportMisClassification(BaseAction):

    def __init__(self) -> None:
        super().__init__(REPORT_MIS_CLASSIFICATION_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.entities_list = self.soar_action.extract_action_param(
            param_name="Entities",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.classification = self.soar_action.extract_action_param(
            param_name="Classification",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.confident = self.soar_action.extract_action_param(
            param_name="Confident",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )

    def _perform_action(self, _=None) -> None:
        entities = self.params.entities_list.split(',')
        classification = MIS_CLASSIFICATION_OPTIONS[self.params.classification]
        confident = MIS_CLASSIFICATION_CONFIDENCE[self.params.confident]

        self.json_results = self.api_client.report_mis_classification(
            entities=entities,
            classification=classification,
            confident=confident
        )


def main() -> None:
    ReportMisClassification().run()


if __name__ == "__main__":
    main()
