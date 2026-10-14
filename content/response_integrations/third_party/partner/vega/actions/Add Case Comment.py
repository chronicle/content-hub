from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


def _add_case_comment(siemplify: SiemplifyAction, comment: str) -> None:
    case = getattr(siemplify, "case", None)
    case_id = getattr(case, "identifier", None) if case is not None else getattr(siemplify, "case_id", None)
    try:
        if case_id:
            siemplify.add_comment(comment=comment, case_id=case_id)
        else:
            siemplify.add_comment(comment)
    except TypeError:
        try:
            siemplify.add_comment(comment, case_id, None)
        except TypeError:
            siemplify.add_comment(comment)


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    from ..core.constants import ADD_CASE_COMMENT_SCRIPT_NAME
    from ..core.utils import format_user_facing_error

    siemplify.script_name = ADD_CASE_COMMENT_SCRIPT_NAME
    try:
        comment = str(siemplify.extract_action_param("Comment", default_value="") or "").strip()
        if not comment:
            raise ValueError("Comment is required.")
        _add_case_comment(siemplify, comment)
        siemplify.result.add_result_json({"comment": comment})
        siemplify.end("Added a case comment.", True, EXECUTION_STATE_COMPLETED)
    except Exception as error:
        message = f'Error executing action "Add Case Comment". Reason: {format_user_facing_error(error)}'
        siemplify.LOGGER.error(message)
        siemplify.end(message, False, EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
