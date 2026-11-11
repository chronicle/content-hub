from __future__ import annotations
from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from scc_enterprise.core import SCCEnterpriseConsts
from scc_enterprise.core import ServiceNowConsts
from scc_enterprise.core import ServiceNowDatamodels
from scc_enterprise.core.ServiceNowExceptions import SNowNotFoundException
from scc_enterprise.core.ServiceNowManager import ServiceNowManager
from scc_enterprise.core import ServiceNowTableFields


class CreateSCCEnterpriseCloudPostureTicketTypeSnow(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            f"Created/updated “{SCCEnterpriseConsts.INTEGRATION_NAME} Cloud Posture "
            "Tickets” record type in SNOW."
        )

    def _init_api_clients(self) -> ServiceNowManager:
        return ServiceNowManager(
            api_root=self.params.api_root,
            username=self.params.username,
            password=self.params.password,
            verify_ssl=self.params.verify_ssl,
            siemplify_logger=self.soar_action.LOGGER,
        )

    def _extract_action_parameters(self) -> None:
        # Manager set up params
        self.params.api_root = extract_action_param(
            self.soar_action, param_name="API Root", print_value=True
        )
        self.params.username = extract_action_param(
            self.soar_action, param_name="Username"
        )
        self.params.password = extract_action_param(
            self.soar_action,
            param_name="Password",
            remove_whitespaces=False,
            print_value=False,
        )
        self.params.verify_ssl = extract_action_param(
            self.soar_action, param_name="Verify SSL", input_type=bool
        )
        self.params.table_role = extract_action_param(
            self.soar_action,
            param_name="Table Role",
            default_value=ServiceNowConsts.CUSTOM_TICKET_USER,
        )

    def _perform_action(self, _=None) -> None:

        table_role = self.get_or_create_table_role()
        self.logger.info(f"Successfully fetched user role - {table_role.name}")

        created_table = self.create_sn_table()
        self.logger.info(f"Successfully created table with name {created_table.name}.")
        self.populate_business_rules()

        application_module = self.create_application_module(table=created_table)
        self.logger.info(
            f"Successfully created app module with name " f"{application_module.title}."
        )

        created_ui_view = self.create_ui_form_view(table=created_table)
        self.logger.info(
            f"Successfully created or updated form view {created_ui_view.title} "
            f"for table {created_table.name}."
        )

        created_ui_view = self.create_ui_list_view(table=created_table)
        self.logger.info(
            f"Successfully created or updated list view {created_ui_view.title} "
            f"for table {created_table.name}."
        )

        test_ticket = ServiceNowDatamodels.SNSCCECloudPostureTicket.create_dummy_entry(
            self.params.username
        )
        _test_ticket = self.api_client.create_or_update_entry(test_ticket)
        self.logger.info(
            f"Added a test entry {_test_ticket.u_ticket_name} "
            f"into {created_table.name}"
        )
        self.json_results = _test_ticket.to_json()

    def get_or_create_table_role(self):
        """
        Get user role if exists, create if it's default.

        Returns:
            ServiceNow User
        """
        user_role = ServiceNowDatamodels.SNUserRole(name=self.params.table_role)
        create_if_not_found = (
            self.params.table_role == ServiceNowConsts.CUSTOM_TICKET_USER
        )

        try:
            return self.api_client.create_or_update_entry(
                entry=user_role, create_if_not_found=create_if_not_found
            )
        except SNowNotFoundException:
            raise SNowNotFoundException(
                "Provided user role wasn't found in Service Now, please check "
                "your input. If the parameter 'Table Role' is left empty, "
                "action will create a new custom role dedicated to "
                f"'{SCCEnterpriseConsts.INTEGRATION_NAME} Cloud Posture Ticket' table."
            )

    def create_sn_table(self) -> ServiceNowDatamodels.SNTable:
        """
        Prepare data models and create Table and Table fields.

        Returns:
            Created ServiceNow Table
        """
        self.logger.info(
            "Preparing data models for Table and Table fields creation..."
        )
        table = ServiceNowDatamodels.SNTable(
            label=ServiceNowConsts.CUSTOM_TICKET_TABLE_LABEL,
            name=ServiceNowConsts.CUSTOM_TICKET_TABLE_NAME,
            user_role=self.params.table_role,
        )
        table_fields = [
            ServiceNowDatamodels.SNTableField(**table_field_attrs)
            for table_field_attrs in ServiceNowTableFields.TABLE_FIELDS_JSON
        ]
        return self.api_client.create_table(table=table, table_fields=table_fields)

    def populate_business_rules(self) -> None:
        """
        Populate custom SNow business rules.

        Returns:
            None
        """
        self.logger.info("Preparing data models for custom Business Rules ...")
        for business_rules_kwargs in ServiceNowTableFields.BUSINESS_RULES:
            business_rule = ServiceNowDatamodels.SNBusinessRule(**business_rules_kwargs)
            self.api_client.create_or_update_entry(business_rule)

    def create_application_module(
        self, table: ServiceNowDatamodels.SNTable
    ) -> ServiceNowDatamodels.SNApplicationModule:
        """
        Prepare data models and create App menu and module.

        Args:
            table: ServiceNow table to create module for

        Returns:
            Created app module
        """
        self.logger.info(
            "Preparing data models for Application Menu and Module creation..."
        )
        application_menu = ServiceNowDatamodels.SNApplicationMenu(
            roles=self.params.table_role,
            title=ServiceNowConsts.APPLICATION_MODULE_TITLE,
            name=ServiceNowConsts.APPLICATION_MODULE_TITLE,
        )
        application_module = ServiceNowDatamodels.SNApplicationModule(
            roles=self.params.table_role,
            title=ServiceNowConsts.APPLICATION_MODULE_TITLE,
            mobile_title=ServiceNowConsts.APPLICATION_MODULE_TITLE,
            name=table.name,
        )
        return self.api_client.create_application(
            application_menu=application_menu, application_module=application_module
        )

    def create_ui_form_view(
        self,
        table: ServiceNowDatamodels.SNTable,
        view_name: str = ServiceNowConsts.DEFAULT_VIEW,
    ) -> ServiceNowDatamodels.SNUiView:
        """
        Prepare data models and create Default view if not exists and form with predefined fields data.

        Args:
            table: Table that form is created for
            view_name: Name for the new (existing view)

        Returns:
            created ui form view
        """
        self.logger.info("Preparing data models for UI Form and View creation...")

        ui_view = ServiceNowDatamodels.SNUiView(
            name=view_name if view_name != ServiceNowConsts.DEFAULT_VIEW else "",
            title=view_name,
        )
        ui_sections = []
        for ui_section_meta in ServiceNowTableFields.VIEW_SECTIONS_MAPPING[view_name]:
            section_fields = []
            for index, field_meta in enumerate(ui_section_meta["fields"]):
                if isinstance(field_meta, str):
                    field_meta = {"element": field_meta}
                section_fields.append(
                    ServiceNowDatamodels.SNUiFormField(
                        **field_meta, position=str(index)
                    )
                )

            ui_sections.append(
                ServiceNowDatamodels.SNUiSection(
                    caption=ui_section_meta["name"],
                    name=table.name,
                    sys_name=ui_section_meta["name"],
                    section_fields=section_fields,
                    position=ui_section_meta["position"],
                )
            )

        return self.api_client.create_form_ui_view(
            table=table, ui_view=ui_view, ui_sections=ui_sections
        )

    def create_ui_list_view(
        self,
        table: ServiceNowDatamodels.SNTable,
        view_name: str = ServiceNowConsts.DEFAULT_VIEW,
    ) -> ServiceNowDatamodels.SNUiView:
        """
        Prepare data models and create view if no exists and ui list.

        Args:
            table: Table that form is created for
            view_name: Name for the new (existing view)

        Returns:
            created ui list view
        """
        self.logger.info("Preparing data models for UI List and View creation...")

        ui_view = ServiceNowDatamodels.SNUiView(
            name=view_name if view_name != ServiceNowConsts.DEFAULT_VIEW else "",
            title=view_name,
        )
        ui_list = ServiceNowDatamodels.SNUiList(
            name=table.name,
            ui_list_elements=[
                ServiceNowDatamodels.SNUiListElement(
                    element=field_name, position=str(index)
                )
                for index, field_name in enumerate(
                    ServiceNowTableFields.VIEW_LIST_MAPPING[view_name]
                )
            ],
        )

        return self.api_client.create_list_ui_view(ui_view=ui_view, ui_list=ui_list)


def main() -> None:
    CreateSCCEnterpriseCloudPostureTicketTypeSnow(
        SCCEnterpriseConsts.SERVICE_NOW_BOOTSTRAP
    ).run()


if __name__ == "__main__":
    main()
