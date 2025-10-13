from base64 import b64encode

from anyrun.connectors import SandboxConnector
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.rest.soar_api import save_attachment_to_case_wall

from ..core.config import Config
from ..core.data_table_manager import DataTableManager
from ..core.utils import prepare_base_params, prepare_report_comment, setup_action_proxy


@output_handler
def main():
    siemplify = SiemplifyAction()

    token = extract_configuration_param(
        siemplify, Config.INTEGRATION_NAME, param_name="ANY.RUN Sandbox API KEY", is_mandatory=True
    )

    attachments = siemplify.get_attachments()

    if not attachments:
        siemplify.end("Attachment is not found.", False, EXECUTION_STATE_FAILED)

    attachment_name, attachment_id = attachments[0].get("name"), attachments[0].get("id")
    attachment_data = siemplify.get_attachment(attachment_id)

    with SandboxConnector.windows(
        token, integration=Config.VERSION, proxy=setup_action_proxy(siemplify)
    ) as connector:
        task_uuid = connector.run_file_analysis(
            attachment_data,
            attachment_name,
            env_version=extract_action_param(siemplify, param_name="env_version"),
            env_bitness=extract_action_param(siemplify, param_name="env_bitness"),
            env_type=extract_action_param(siemplify, param_name="env_type"),
            obj_ext_startfolder=extract_action_param(siemplify, param_name="obj_ext_startfolder"),
            obj_ext_cmd=extract_action_param(siemplify, param_name="obj_ext_cmd"),
            obj_force_elevation=extract_action_param(siemplify, param_name="obj_force_elevation"),
            **prepare_base_params(siemplify),
        )

        siemplify.add_comment(
            f"Link to the ANY.RUN interactive analysis: https://app.any.run/tasks/{task_uuid}"
        )

        for status in connector.get_task_status(task_uuid):
            siemplify.LOGGER.info(status)

        report = connector.get_analysis_report(task_uuid, report_format="html")

        save_attachment_to_case_wall(
            siemplify,
            CaseWallAttachment(
                f"{attachment_name[:15]}_anyrun_sandbox_report",
                ".html",
                b64encode(report.encode()).decode(),
                True,
            ),
        )

        if iocs := connector.get_analysis_report(task_uuid, report_format="ioc"):
            data_tables = DataTableManager(siemplify)
            data_tables.update_sandbox_indicators(iocs, task_uuid)
            siemplify.add_comment(prepare_report_comment(iocs))

        status = connector.get_analysis_verdict(task_uuid)
        siemplify.end(
            f"File analysis for the entity: {attachment_name} is successfully ended. "
            f"Analysis status: {status}.",
            False,
            EXECUTION_STATE_COMPLETED,
        )


if __name__ == "__main__":
    main()
