from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.UtilsManager import get_case_and_ticket_ids, write_sync_data, read_sync_data
from ..core.RSAArcherManager import RSAArcherManager
from ..core.constants import (
    DEVICE_PRODUCT,
    SYNC_SECURITY_INCIDENTS_SCRIPT_NAME,
    SECURITY_INCIDENTS_APP_NAME,
    SECURITY_INCIDENTS_FIELD,
    SYNC_FIELDS,
)
from soar_sdk.SiemplifyJob import SiemplifyJob

OPEN_CASE_STATUS = "1"
CLOSE_CASE_STATUS = "2"
INCIDENT_JOURNAL_FIELD = "Incident_Journal"


@output_handler
def main():
    siemplify = SiemplifyJob()

    try:
        siemplify.script_name = SYNC_SECURITY_INCIDENTS_SCRIPT_NAME

        siemplify.LOGGER.info("--------------- JOB STARTED ---------------")

        api_root = siemplify.extract_job_param(param_name="API Root", is_mandatory=True)
        username = siemplify.extract_job_param(param_name="Username", is_mandatory=True)
        password = siemplify.extract_job_param(param_name="Password", is_mandatory=True)
        verify_ssl = siemplify.extract_job_param(
            param_name="Verify SSL", is_mandatory=True, input_type=bool
        )
        sync_fields = siemplify.extract_job_param(
            param_name="Sync Fields", is_mandatory=True
        )
        instance_name = siemplify.extract_job_param(
            param_name="Instance Name", is_mandatory=True
        )

        manager = RSAArcherManager(
            api_root=api_root,
            username=username,
            password=password,
            instance_name=instance_name,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            siemplify=siemplify,
        )

        open_case_ids = siemplify.get_cases_by_filter(
            case_names=[DEVICE_PRODUCT], statuses=[OPEN_CASE_STATUS]
        )

        open_cases = [siemplify._get_case_by_id(case_id) for case_id in open_case_ids]

        siemplify.LOGGER.info(f"Found {len(open_cases)} open cases to process")

        ticket_ids_by_case_id = [get_case_and_ticket_ids(case) for case in open_cases]

        sync_data = read_sync_data(siemplify)

        sync_fields_list = [f.strip() for f in sync_fields.split(",")]

        sync_fields_json = []
        security_incidents_json = []

        siemplify.LOGGER.info("--- Started Synchronizing Security Incidents Fields ---")

        if (
            len(
                set(
                    [field.get("name") for field in sync_data.get(SYNC_FIELDS, [])]
                ).symmetric_difference(sync_fields_list)
            )
            > 0
        ):
            application = manager.get_app_by_name(app_name=SECURITY_INCIDENTS_APP_NAME)
            app_fields = manager.get_fields(application_id=application.id)
            for field in sync_fields_list:
                alias = next(
                    (
                        app_field.alias
                        for app_field in app_fields
                        if app_field.name == field
                    ),
                    None,
                )
                if alias:
                    sync_fields_json.append({"name": field, "alias": alias})
                else:
                    siemplify.LOGGER.error(
                        f"Provided field {field} was not found in application fields"
                    )

            sync_data[SYNC_FIELDS] = sync_fields_json

        # query each incident and check the field value from API with the one in json file
        for item in ticket_ids_by_case_id:
            general_comments = []
            journal_entries = {}
            ticket_id = list(item.values())[0]
            case_id = list(item.keys())[0]
            siemplify.LOGGER.info(f"Started processing incident {ticket_id}.")
            security_incident = manager.get_security_incident_details(
                incident_id=ticket_id
            )
            incident_json = next(
                (
                    data
                    for data in sync_data.get(SECURITY_INCIDENTS_FIELD)
                    if data.get("id") == ticket_id
                ),
                None,
            )
            incident_json = (
                incident_json
                if incident_json
                else {"id": ticket_id, "fields": security_incident}
            )
            all_aliases = [
                field.get("alias") for field in sync_data.get(SYNC_FIELDS, [])
            ]
            all_aliases = (
                all_aliases
                if INCIDENT_JOURNAL_FIELD in all_aliases
                else all_aliases + [INCIDENT_JOURNAL_FIELD]
            )
            for field_alias in all_aliases:
                previous_value = incident_json.get("fields", {}).get(field_alias)
                new_value = security_incident.get(field_alias)
                if previous_value is not None:
                    if previous_value != new_value:
                        incident_json.get("fields")[field_alias] = new_value
                        if field_alias == INCIDENT_JOURNAL_FIELD:
                            new_journal_entries = list(
                                set(new_value).difference(previous_value)
                            )
                            for entry in new_journal_entries:
                                try:
                                    incident_journal = (
                                        manager.get_incident_journal_details(
                                            incident_journal_id=entry
                                        )
                                    )
                                    new_comment = (
                                        "The following Incident Journal Entry was added to the Security "
                                        "Incident {}: {}".format(
                                            ticket_id,
                                            incident_journal.get("Journal_Entry", ""),
                                        )
                                    )
                                    journal_entries[
                                        incident_journal.get("Journal_ID")
                                    ] = incident_journal.get("Journal_Entry")
                                    siemplify.LOGGER.info(new_comment)
                                except Exception as e:
                                    siemplify.LOGGER.error(
                                        f"Failed to get details for incident journal {entry}."
                                    )
                                    siemplify.LOGGER.exception(e)
                        else:
                            new_comment = f"\"{field_alias}\": \"{', '.join(previous_value) if isinstance( previous_value, list) else previous_value}\" -> \"{', '.join(new_value) if isinstance( new_value, list) else new_value}\""
                            general_comments.append(new_comment)
                            siemplify.LOGGER.info(
                                f"The following field was updated: {new_comment}"
                            )
                else:
                    incident_json.get("fields")[field_alias] = new_value

            security_incidents_json.append(incident_json)

            siemplify.LOGGER.info(f"Adding comments to case {case_id} in Siemplify.")

            comments = []
            if journal_entries:
                comments.append(
                    "The following Incident Journal Entries were added to the Security Incident {}:\n{}".format(
                        ticket_id,
                        "".join(
                            [
                                f"{i+1}. Journal Entry {k} {v}"
                                for i, (k, v) in enumerate(journal_entries.items())
                            ]
                        ),
                    )
                )
            if general_comments:
                comments.append(
                    (
                        f"The following fields were updated for Security Incident {ticket_id}:\n"
                        + "\n".join(general_comments)
                    )
                )

            comment_to_add = "\n\n".join(comments)
            if comment_to_add:
                try:
                    siemplify.add_comment(comment_to_add, case_id, None)
                    siemplify.LOGGER.info(
                        f"Added new comment to case with id: {case_id}"
                    )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to add comment to case {case_id}, Reason: {e}"
                    )
                    siemplify.LOGGER.exception(e)

            else:
                siemplify.LOGGER.info(f"No new comments to add to case {case_id}.")
            siemplify.LOGGER.info(f"Finished processing incident {ticket_id}.")

        siemplify.LOGGER.info(
            "--- Finished Synchronizing Security Incidents Fields ---"
        )

        sync_data[SECURITY_INCIDENTS_FIELD] = security_incidents_json
        write_sync_data(siemplify, sync_data)

        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler.Error: {e}")
        siemplify.LOGGER.exception(e)


if __name__ == "__main__":
    main()
