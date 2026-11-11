from __future__ import annotations

import dataclasses
import datetime

from TIPCommon.transformation import dict_to_flat, flat_dict_to_csv
from TIPCommon.types import JSON, SingleJson
from scc_enterprise.core import SCCEnterpriseConsts
from scc_enterprise.core import ServiceNowConsts


class BaseModel:

    def __init__(self, raw_data: JSON) -> None:
        self.raw_data = raw_data

    def to_json(self) -> JSON:
        return self.raw_data

    def is_empty(self) -> bool:
        return not bool(self.raw_data)

    def to_csv(self) -> list[str]:
        return flat_dict_to_csv(dict_to_flat(self.raw_data))


class Incident(BaseModel):

    def __init__(
        self,
        raw_data: SingleJson,
        sys_id: str | None = None,
        sys_created_on: str | None = None,
        sys_created_by: str | None = None,
        status: str | int | None = None,
        overview: str | None = None,
        priority: str | None = None,
        severity: str | None = None,
        assignee: str | dict[str, str] | None = None,
        case_uri: str = "",
    ) -> None:
        super(Incident, self).__init__(raw_data)
        self.severity = severity
        self.assignee = assignee
        self.priority = priority
        self.overview = overview
        self.sys_id = sys_id
        self.status = status
        self.sys_created_on = sys_created_on
        self.sys_created_by = sys_created_by
        self.case_uri = case_uri

    def __repr__(self) -> str:
        return f"Incident object {self.sys_id}"

    def update_incident_with_user_info(self, user_info) -> None:
        self.raw_data.update(self._get_user_info(user_info))

    @staticmethod
    def _get_user_info(user_info) -> SingleJson:
        return {
            "caller_name": user_info.name,
            "caller_username": user_info.username,
            "caller_email_address": user_info.email,
            "opened_by_name": user_info.name,
            "opened_by_username": user_info.username,
            "opened_by_email_address": user_info.email,
        }


@dataclasses.dataclass
class Comment(BaseModel):
    raw_data: SingleJson
    value: str
    sys_created_on: str
    element_id: str


@dataclasses.dataclass
class Ticket(BaseModel):
    raw_data: SingleJson
    state: str
    sys_id: str
    number: str

    def get_value(self, key: str) -> str:
        field: str | SingleJson = self.raw_data.get(key, "")
        if isinstance(field, str):
            return field.lower()

        return field.get("display_value", "").lower() or field.get("value", "").lower()

    @property
    def is_open(self) -> bool:
        return self.state.casefold() not in {
            status.casefold() for status in SCCEnterpriseConsts.CLOSED_STATUSES
        }


class SNBaseEntry:

    def __init__(self, **kwargs) -> None:
        self.raw_data = kwargs.get("raw_data")
        self.sys_id = kwargs.get("sys_id")

        self.table_name = None

    def to_json(self) -> dict:
        return self.raw_data

    def to_search_params(self) -> dict:
        return self.to_json()


class SNSCCECloudPostureTicket(SNBaseEntry):

    def __init__(
        self,
        u_assigned_to: str,
        u_ticket_name: str,
        u_severity: str,
        u_status: str,
        u_cloud_environment: str,
        u_priority: str,
        u_due_date: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.u_assigned_to = u_assigned_to
        self.u_ticket_name = u_ticket_name
        self.u_severity = u_severity
        self.u_status = u_status
        self.u_cloud_environment = u_cloud_environment
        self.u_priority = u_priority
        self.u_due_date = u_due_date

        self.table_name = ServiceNowConsts.CUSTOM_TICKET_TABLE_NAME

    @classmethod
    def create_dummy_entry(cls, username: str) -> SNSCCECloudPostureTicket:
        return cls(
            u_assigned_to=username,
            u_ticket_name="Posture Test Ticket",
            u_severity="Info",
            u_status="Open",
            u_cloud_environment="Google Cloud",
            u_priority="Low",
            u_due_date=(
                (datetime.datetime.now() - datetime.timedelta(days=14)).strftime(
                    ServiceNowConsts.DATETIME_FORMAT
                )
            ),
        )

    def to_json(self) -> SingleJson:
        if self.raw_data is not None:
            return self.raw_data

        return {
            "u_assigned_to": self.u_assigned_to,
            "u_ticket_name": self.u_ticket_name,
            "u_severity": self.u_severity,
            "u_status": self.u_status,
            "u_cloud_environment": self.u_cloud_environment,
            "u_priority": self.u_priority,
            "u_due_date": self.u_due_date,
        }

    def to_search_params(self) -> SingleJson:
        return {"u_ticket_name": self.u_ticket_name}


class SNUserRole(SNBaseEntry):

    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name

        self.table_name = "sys_user_role"

    def to_json(self) -> SingleJson:
        return {"name": self.name}


class SNTable(SNBaseEntry):

    def __init__(
        self,
        label: str,
        name: str,
        user_role: str,
        create_access_controls: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.label = label
        self.name = name
        self.user_role = user_role
        self.create_access_controls = create_access_controls

        self.table_name = "sys_db_object"

    def to_json(self) -> SingleJson:
        return {
            "label": self.label,
            "name": self.name,
            "user_role": self.user_role,
            "create_access_controls": self.create_access_controls,
        }

    def to_search_params(self) -> SingleJson:
        return {"name": self.name}


class SNTableField(SNBaseEntry):

    def __init__(
        self,
        element: str,
        max_length: str,
        column_label: str,
        internal_type: str | dict,
        name: str = "",
        read_only: str = "false",
        unique: str = "false",
        mandatory: str = "false",
        display: str = "false",
        default_value: str = "",
        reference: str | dict = "",
        choices: list[str] | None = None,
        choice: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.read_only = read_only
        self.element = element
        self.max_length = max_length
        self.unique = unique
        self.name = name
        self.mandatory = mandatory
        self.column_label = column_label
        self.display = display
        self.default_value = default_value
        self.internal_type = internal_type
        self.reference = reference
        self.choice = choice

        self.choices = choices
        self.table_name = "sys_dictionary"

    def to_json(self) -> SingleJson:
        return {
            "read_only": self.read_only,
            "element": self.element,
            "max_length": self.max_length,
            "unique": self.unique,
            "name": self.name,
            "mandatory": self.mandatory,
            "column_label": self.column_label,
            "display": self.display,
            "default_value": self.default_value,
            "internal_type": self.internal_type,
            "reference": self.reference,
            "choice": self.choice,
        }

    def to_search_params(self) -> SingleJson:
        return {"name": self.name, "element": self.element}


class SNChoice(SNBaseEntry):

    def __init__(
        self, element: str, name: str, label: str, value: str, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.element = element
        self.name = name
        self.label = label
        self.value = value

        self.table_name = "sys_choice"

    def to_json(self) -> SingleJson:
        return {
            "element": self.element,
            "name": self.name,
            "label": self.label,
            "value": self.value,
        }

    def to_search_params(self) -> SingleJson:
        return {"element": self.element, "name": self.name, "label": self.label}


class SNBusinessRule(SNBaseEntry):
    def __init__(
        self,
        action_delete: bool,
        action_insert: bool,
        action_update: bool,
        collection: str,
        filter_condition: str,
        name: str,
        template: str,
        when: str,
        advanced: bool = False,
        change_fields: bool = False,
        sys_scope: str = "global",
        sys_package: str = "global",
        order: int = 100,
        priority: int = 100,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.action_delete = action_delete
        self.action_insert = action_insert
        self.action_update = action_update
        self.collection = collection
        self.filter_condition = filter_condition
        self.name = name
        self.template = template
        self.when = when
        self.advanced = advanced
        self.change_fields = change_fields
        self.sys_scope = sys_scope
        self.sys_package = sys_package
        self.order = order
        self.priority = priority

        self.table_name = "sys_script"

    def to_json(self) -> SingleJson:
        return {
            "template": self.template,
            "action_insert": self.action_insert,
            "action_update": self.action_update,
            "advanced": self.advanced,
            "action_delete": self.action_delete,
            "change_fields": self.change_fields,
            "when": self.when,
            "sys_scope": self.sys_scope,
            "order": self.order,
            "collection": self.collection,
            "priority": self.priority,
            "filter_condition": self.filter_condition,
            "sys_package": self.sys_package,
            "name": self.name,
        }

    def to_search_params(self) -> SingleJson:
        return {"name": self.name, "collection": self.collection}


class SNApplicationMenu(SNBaseEntry):

    def __init__(
        self,
        roles: str,
        title: str,
        name: str,
        category: str = "Custom Applications",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.roles = roles
        self.title = title
        self.name = name
        self.category = category

        self.table_name = "sys_app_application"

    def to_json(self) -> SingleJson:
        return {
            "roles": self.roles,
            "title": self.title,
            "name": self.name,
            "category": self.category,
        }

    def to_search_params(self) -> SingleJson:
        return {"name": self.name, "title": self.title}


class SNApplicationModule(SNBaseEntry):

    def __init__(
        self,
        roles: str,
        title: str,
        mobile_title: str,
        name: str,
        application: str | dict = "",
        mobile_view_name: str = "Mobile",
        link_type: str = "LIST",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.roles = roles
        self.title = title
        self.name = name
        self.mobile_title = mobile_title
        self.application = application
        self.mobile_view_name = mobile_view_name
        self.link_type = link_type

        self.table_name = "sys_app_module"

    def to_json(self) -> SingleJson:
        return {
            "roles": self.roles,
            "title": self.title,
            "name": self.name,
            "mobile_title": self.mobile_title,
            "application": self.application,
            "mobile_view_name": self.mobile_view_name,
            "link_type": self.link_type,
        }

    def to_search_params(self) -> SingleJson:
        return {"name": self.name, "title": self.title, "application": self.application}


class SNUiView(SNBaseEntry):

    def __init__(self, name: str, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.title = title

        self.table_name = "sys_ui_view"

    def to_json(self) -> SingleJson:
        return {"name": self.name, "title": self.title}

    def to_search_params(self) -> SingleJson:
        return {"title": self.title}


class SNUiForm(SNBaseEntry):

    def __init__(self, name: str, view: str | dict = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.view = view

        self.table_name = "sys_ui_form"

    def to_json(self) -> SingleJson:
        return {"name": self.name, "view": self.view}

    def to_search_params(self) -> SingleJson:
        return {"view": self.view, "name": self.name}


class SNUiSection(SNBaseEntry):

    def __init__(
        self,
        name: str,
        caption: str,
        sys_name: str,
        title: str = "true",
        view: str | dict = "",
        section_fields: list[SNUiFormField] = None,
        position: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.title = title
        self.caption = caption
        self.sys_name = sys_name
        self.view = view

        # Non-native fields
        self.section_fields: list[SNUiFormField] = section_fields
        self.position = position

        self.table_name = "sys_ui_section"

    def to_json(self) -> SingleJson:
        return {
            "caption": self.caption,
            "title": self.title,
            "view": self.view,
            "name": self.name,
            "sys_name": self.sys_name,
        }

    def to_search_params(self) -> SingleJson:
        return {"name": self.name, "view": self.view, "sys_name": self.sys_name}


class SNUiFormSection(SNBaseEntry):

    def __init__(
        self, sys_ui_form: str, sys_ui_section: str, position: str, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.sys_ui_form = sys_ui_form
        self.sys_ui_section = sys_ui_section
        self.position = position

        self.table_name = "sys_ui_form_section"

    def to_json(self) -> SingleJson:
        return {
            "sys_ui_form": self.sys_ui_form,
            "sys_ui_section": self.sys_ui_section,
            "position": self.position,
        }

    def to_search_params(self) -> SingleJson:
        return {"sys_ui_form": self.sys_ui_form, "sys_ui_section": self.sys_ui_section}


class SNSystemProperty(SNBaseEntry):

    def __init__(
        self,
        description: str,
        name: str,
        value: str,
        write_roles: str = "",
        read_roles: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.description = description
        self.name = name
        self.value = value
        self.write_roles = write_roles
        self.read_roles = read_roles
        self.type_ = kwargs.get("type", "string")

        self.table_name = "sys_properties"

    def to_json(self) -> SingleJson:
        return {
            "description": self.description,
            "type": self.type_,
            "write_roles": self.write_roles,
            "name": self.name,
            "read_roles": self.read_roles,
            "value": self.value,
        }

    def to_search_params(self) -> SingleJson:
        return {"name": self.name}


class SNUiFormField(SNBaseEntry):

    def __init__(
        self,
        position: str,
        element: str,
        sys_ui_section: str | dict = "",
        sys_ui_formatter: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.element = element
        self.sys_ui_section = sys_ui_section
        self.position = position
        self.sys_ui_formatter = sys_ui_formatter
        self.type_ = kwargs.get("type")

        self.table_name = "sys_ui_element"

    def to_json(self) -> SingleJson:
        return {
            "element": self.element,
            "sys_ui_section": self.sys_ui_section,
            "position": self.position,
            "sys_ui_formatter": self.sys_ui_formatter,
            "type": self.type_,
        }

    def to_search_params(self) -> SingleJson:
        return {"element": self.element, "sys_ui_section": self.sys_ui_section}


class SNUiList(SNBaseEntry):

    def __init__(
        self,
        name: str,
        view: str | dict = "",
        ui_list_elements: list[SNUiListElement] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.view = view

        # Non-native fields
        self.list_fields = ui_list_elements
        self.table_name = "sys_ui_list"

    def to_json(self) -> SingleJson:
        return {"name": self.name, "view": self.view}

    def to_search_params(self) -> SingleJson:
        return {"view": self.view, "name": self.name}


class SNUiListElement(SNBaseEntry):

    def __init__(
        self, position: str, element: str, list_id: str | dict = "", **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.element = element
        self.list_id = list_id
        self.position = position

        self.table_name = "sys_ui_list_element"

    def to_json(self) -> SingleJson:
        return {
            "element": self.element,
            "list_id": self.list_id,
            "position": self.position,
        }

    def to_search_params(self) -> SingleJson:
        return {"element": self.element, "list_id": self.list_id}
