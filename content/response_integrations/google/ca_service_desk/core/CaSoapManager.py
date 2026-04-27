#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ==============================================================================
# title           :CaSoapManager.py
# description     :This Module contain all CA Desk operations functionality using Soap API
# author          :zdemoniac@gmail.com
# date            :1-9-18
# python_version  :2.7
# libraries       : time, xml, zeep
# requirements    : pip install zeep, ticketFields names in CA
# product_version : 12
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
from time import mktime

import defusedxml.ElementTree as ET
from zeep.client import Client

# =====================================
#             CONSTANTS               #
# =====================================

API_ROOT_URL = "/axis/services/USD_R11_WebService?wsdl"

TICKET_STATUS_FIELD = "status.sym"
TICKET_STATUS_ID_FIELD = "status"


# =====================================
#              CLASSES                #
# =====================================
class CaManagerError(Exception):
    """
    General Exception for CA manager
    """

    pass


class CaSoapManager:
    """
    Responsible for all CA Desk operations functionality
    """

    def __init__(self, url, user_name, password):
        self._url = f"{url}{API_ROOT_URL}"
        self._user_name = user_name
        self._user_password = password
        self._client = Client(self._url)
        self._sid = None
        self._tf = self._client.type_factory(
            "http://www.ca.com/UnicenterServicePlus/ServiceDesk"
        )
        self._login()

    def test_connectivity(self):
        """
        Validates connectivity
        :return: {boolean} True/False
        """
        return self._login()

    def _login(self):
        """
        Open new session with CA Desk Manager
        :return:
        """
        try:
            self._sid = self._client.service.login(self._user_name, self._user_password)
        except Exception as error:
            raise CaManagerError(f"Error in _login() {error}")
        return True

    def create_incident(
        self,
        summary,
        description="",
        area="",
        group="",
        severity="",
        urgency=2,
        problem_type="",
        user_id="",
        **kwargs,
    ):
        """
        Create new incident in CA Desk using creatTicket soup method
        :param summary: {string} incident's summary text
        :param description: {string} incident's description text
        :param area: {string} incident's area id
        :param group: {string}
        :param severity {int} 0-escalated, 1-supervisor, 2-Mgr, 3-HD Mgr, 4-All Hands Escalation
        :param urgency {int}
        :param problem_type: {int} the code (not the persistent ID) for an existing problem type
        :param user_id: {string} user
        :param **kwargs: {dict} additional arguments, Custom fields.

        :return: {string} Created incident id
        """
        if not user_id:
            user = ""
        else:
            user = self._client.service.getHandleForUserid(self._sid, user_id)

        result = self._client.service.createTicket(
            self._sid, description, problem_type, user, "", "", "", "", "", ""
        )
        if result is not None:
            ref_num = self.get_incident_ref_num_by_id(result.newTicketHandle)
            self.update_incident(
                ref_num, summary, area, group, severity, urgency, **kwargs
            )
            return ref_num
        raise CaManagerError("Error occurred creating a ticket.")

    def get_user_id_by_name(self, user_name):
        """
        Receive user id by it's name.
        :param user_name: user name {string}
        :return: user system id {string}
        """
        user_handle_xml = self._do_select(
            "agt",
            f"combo_name like '{str(user_name).encode('utf-8')}'",
            1,
            ["combo_name"],
        )
        user_handle = ET.fromstring(str(user_handle_xml).encode("utf-8")).find(
            ".//Handle"
        )

        if user_handle is None:
            raise CaManagerError(f"User not found: {user_name}")
        return user_handle.text

    def create_incident_openreq(
        self,
        summary,
        description="",
        area="",
        group="",
        severity="",
        urgency=2,
        username="",
        **kwargs,
    ):
        """
        Create new incident in CA Desk using creatRequest soup method
        :param summary: {string} incident's summary text
        :param description: {string} incident's description text
        :param area: {string} incident's area name
        :param group: {string} group name
        :param severity {int} 0-escalated, 1-supervisor, 2-Mgr, 3-HD Mgr, 4-All Hands Escalation
        :param urgency {int}
        :param username: {string} user name
        :param **kwargs: {dict} additional arguments, Custom fields.
        :return: {string} Created incident id
        """
        area_id = self.get_incident_area_id(area)
        group_id = self.get_group_id_by_name(group)
        user_id_uuid = self._client.service.getHandleForUserid(self._sid, username)

        if area_id is None:
            raise CaManagerError(f"Bad Area(Category) name: {area}")
        if group_id is None:
            raise CaManagerError(f"Bad Group name: {group}")
        if user_id_uuid is None:
            raise CaManagerError(f"Bad user_: {username}")

        request_list = [
            "summary",
            summary,
            "description",
            description,
            "category",
            area_id,
            "group",
            group_id,
            "severity",
            severity,
            "customer",
            user_id_uuid,
            "urgency",
            urgency,
            "type",
            "I",
        ]  # R for request, I for incident, fields are the same

        # Add kwargs values to the request list.
        for key, val in list(kwargs.items()):
            request_list.append(key)
            request_list.append(val)

        attr_val = self._tf.ArrayOfString(request_list)
        prop_val = self._tf.ArrayOfString(["ref_num"])
        attrib = self._tf.ArrayOfString(["customer"])
        result = self._client.service.createRequest(
            self._sid, user_id_uuid, attr_val, prop_val, "", attrib, "", ""
        )
        return result.newRequestNumber

    def update_incident(
        self, ref_num, summary, area="", group="", severity="", urgency=2, **kwargs
    ):
        """
        Update incident in CA Desk
        :param ref_num: {string} incident's ref num
        :param summary: {string} incident's summery to update  incident's summary text
        :param area: {string} incident's area to update  incident's area id
        :param group: {string} incident's group to update
        :param severity: {int} 0-escalated, 1 - supervisor, 2 - Mgr, 3- HD Mgr, 4 - All Hands Escalation
        :param urgency: {int} 0="1-When Possible" 1="2-Soon" 2="3-Quickly" 3="4-Very Quickly" 4="5-Immediate"
        :param **kwargs: {dict} additional arguments, Custom fields.
        :return: {string} result of the update
        """
        try:
            incident_id = self.get_incident_id_by_ref_num(ref_num)
            area_id = self.get_incident_area_id(area)
            group_id = self.get_group_id_by_name(group)
            if incident_id is None:
                raise CaManagerError(f"Incident num {ref_num} not found")
            if area_id is None:
                raise CaManagerError(f"Bad Area(Category) name: {area}")
            if group_id is None:
                raise CaManagerError(f"Bad Group name: {group}")

            update_list = [
                "summary",
                summary,
                "category",
                area_id,
                "group",
                group_id,
                "severity",
                severity,
                "urgency",
                urgency,
            ]

            # Add kwargs values to the request list.
            for key, val in list(kwargs.items()):
                update_list.append(key)
                update_list.append(val)

            result = self._client.service.updateObject(
                self._sid,
                incident_id,
                self._tf.ArrayOfString(update_list),
                self._tf.ArrayOfString(["ref_num"]),
            )
        except Exception as error:
            raise CaManagerError(f"Error in update_incident() {error}")
        updated_value = ET.fromstring(result.encode("utf-8")).find(".//AttrValue")

        if updated_value is not None:
            return updated_value.text
        raise CaManagerError(f'Error updating incident with id "{ref_num}"')

    def get_incident_area_id(self, area_name):
        """
        Return incident's area Id by name in CA Desk
        :param area_name: area name {string}
        :return: area system id {string}
        """
        result = self._do_select(
            "pcat", f"sym like '{area_name.encode('utf-8')}'", 1, ["persistent_id"]
        )

        persistent_id = ET.fromstring(result.encode("utf-8")).find(".//Handle")
        if persistent_id is not None:
            return persistent_id.text
        raise CaManagerError(f'No area "{area_name}" exist.')

    def add_comment_to_incident(self, ref_num, comment, internal_flag=0):
        """
        Create new ticket in CA Desk
        :param ref_num: incident's ref num {string}
        :param comment: comment to add to an incident {string}
        :param internal_flag: internal comment flag {int}
        :return: {boolean} result status
        """
        try:
            incident_id = self.get_incident_id_by_ref_num(ref_num)
            self._client.service.logComment(
                self._sid, incident_id, comment, internal_flag
            )
        except Exception as error:
            raise CaManagerError(f"Error in add_comment_to_incident() {error}")

        return True

    def close_incident(self, ref_num, description=""):
        """
        Close incident in CA Desk
        :param ref_num: incident's ref num {string}
        :param description: description which can be used in the Close activity log. {string} (Optional)
        :return: Closed ticket id {string}
        """
        try:
            incident_id = self.get_incident_id_by_ref_num(ref_num)
            result = self._client.service.closeTicket(
                self._sid, description, incident_id
            )
        except Exception as error:
            raise CaManagerError(f"Error in close_incident() {error}")

        updated_value = ET.fromstring(result).find(".//Handle")

        if updated_value is not None:
            return updated_value.text
        raise CaManagerError(f"Error occurred closing incident with id: {ref_num}")

    def get_incident_id_by_ref_num(self, ref_num):
        """
        Get incident Handle by ref num in CA Desk
        :param ref_num: incident's ref num {string}
        :return: incident persistent_id {string}
        """
        result = self._do_select(
            "in", f"ref_num like '{ref_num}'", 1, ["persistent_id"]
        )
        persistent_id = ET.fromstring(result).find(".//AttrValue")
        if persistent_id is not None:
            return persistent_id.text
        raise CaManagerError(f"Not found incident with id: {ref_num}")

    def get_incident_ref_num_by_id(self, persistent_id):
        """
        Get incident Handle by ref num in CA Desk
        :param persistent_id: incident's persistent id {string}
        :return: incident ref_num {string}
        """
        result = self._do_select(
            "in", f"persistent_id like '{persistent_id}'", 1, ["ref_num"]
        )
        ref_num = ET.fromstring(result).find(".//AttrValue")
        if ref_num is not None:
            return ref_num.text
        raise CaManagerError(f'No incident with persistent id "{persistent_id}" found.')

    def get_incident_comments_since_time(
        self, ref_num, start_time_unixtime_milliseconds
    ):
        """
        Get ticket info in CA Desk
        :param ref_num: incident's ref num {string}
        :param start_time_unixtime_milliseconds: time to fetch the comments since {long}
        :return: comments {list}
        """
        comments_result_list = []
        result = self._do_select(
            "alg",
            f"call_req_id.ref_num like '{ref_num}' and time_stamp > {start_time_unixtime_milliseconds / 1000}",
            -1,
            ["time_stamp", "analyst.combo_name", "description", "type.sym"],
        )

        # Fetch comments objects.
        comments = ET.fromstring(result.encode("utf-8")).findall(".//UDSObject")
        # Process Comments.
        for comment in comments:
            # Get Comment attributes(Will be one attributes object for each comment).
            comment_attributes = comment.findall(".//Attributes")[0].getchildren()
            # define new comment dict.
            comment_dict = {}
            for attribute in comment_attributes:
                comment_dict[attribute.findall(".//AttrName")[0].text] = (
                    attribute.findall(".//AttrValue")[0].text
                )

            comments_result_list.append(comment_dict)

        return comments_result_list

    def get_incident_ids_by_filter(
        self,
        summary_filter="",
        description_filter="",
        area_filter="",
        assigned_user_filter="",
        start_unixtime_milliseconds=0,
        last_modification_unixtime_milliseconds=0,
        group_filter="",
        status_filter="",
    ):
        """
        Get tickets by filters (if a filter's string == "": pass the filter)
        :param summary_filter: summery content to filter by {string}s
        :param description_filter: description content to filter by {string}
        :param area_filter: area value to filter by {string} category
        :param assigned_user_filter: assign user to filter by {string}
        :param start_unixtime_milliseconds: incident start time {long}
        :param group_filter: group value to filter by {string}
        :param last_modification_unixtime_milliseconds: last incident modification time {long}
        :param description_filter: description value to filter by {string}
        :return: incident ids {array}
        """
        where = f"open_date > {start_unixtime_milliseconds / 1000} "
        where += f"and last_mod_dt > {last_modification_unixtime_milliseconds / 1000} "

        if summary_filter:
            where += f"and summary like '%{summary_filter}%' "
        if description_filter:
            where += f"and description like '%{description_filter}%' "
        if area_filter:
            where += f"and category.sym like '%{area_filter}%' "
        if assigned_user_filter:
            where += f"and assignee.userid like '%{assigned_user_filter}%' "
        if group_filter:
            where += f"and group.last_name like '%{group_filter}%' "
        if status_filter:
            where += f"and status like '%{status_filter}%' "
        return self.get_incident_ids_where(where)

    def get_close_incident_ids_since_time(self, start_datetime):
        """
        Get closed tickets after start_datetime
        :param start_datetime: closed incidents since start time {datetime}
        :return: incident ref_nums {array}
        """
        where = f"close_date > {int(mktime(start_datetime.timetuple()))}"
        return self.get_incident_ids_where(where)

    def get_incident_ids_where(self, where):
        """
        Get closed tickets after start_datetime
        :param where: a query to get incidents by {string}
        :return: incident ids {array}
        """
        result = self._do_select("in", where, -1, ["ref_num"])
        ref_nums = ET.fromstring(result).findall(".//AttrValue")
        return [ref_num.text for ref_num in ref_nums]

    def get_incident_by_id(self, ref_num, ticket_fields):
        """
        Get incident data by id.
        :param ref_num: incident's ref num {string}
        :param ticket_fields: {list of strings} Ticket fields configure in CA to return in ticket data, those fields are different from server to server
        :return: {dict} incident data
        """
        # Send query to CA Desk Manager.
        result = self._do_select("in", f"ref_num like '{ref_num}'", 1, ticket_fields)

        attr = ET.fromstring(result.encode("utf-8")).findall(".//AttrValue")
        ticket_dict = {}
        if attr:
            for field_name, xml_attr in zip(ticket_fields, attr):
                ticket_dict[field_name] = xml_attr.text
            return ticket_dict
        raise CaManagerError(f"Error incident {ref_num} not found")

    def get_group_id_by_name(self, name):
        """
        :param name: {string} group's name
        :return: {string} group's persistent_id
        """
        # Send query to CA Desk Manager.
        result = self._do_select(
            "grp",
            f"last_name like '{name.encode('utf-8')}'",
            1,
            ["persistent_id", "last_name"],
        )
        persistent_id = ET.fromstring(result.encode("utf-8")).find(".//AttrValue")

        if persistent_id is not None:
            return persistent_id.text
        raise CaManagerError(f"Error group {name} not found")

    def _do_select(self, object_type, where, max_rows, attributes):
        """
        Send query to CA Desk Manager {string}
        :param object_type: Which ticket object to fetch {string}
        :param where: query {string}
        :param max_rows: max amount of rows to fetch {string}
        :param attributes: attributes {string}
        :return: query results {dict}
        """
        try:
            result = self._client.service.doSelect(
                self._sid,
                object_type,
                where,
                max_rows,
                self._tf.ArrayOfString(attributes),
            )
        except Exception as error:
            raise CaManagerError(f"Error in _do_select() {error}")
        return result

    def get_incident_attachments(self, ref_num):
        """
        Get incident attachments in CA Desk
        :param ref_num: {string}
        :return: {dict} attachments data
        """
        # https://docops.ca.com/ca-service-management/14-1/en/reference/
        # ca-service-desk-manager-reference-commands/data-element-dictionary/
        # attachment#Attachment-usp_lrel_attachments_issuesTable

        # Get attachments data by query when the ticket ref num is converted to an inner ID.
        result = self._do_select(
            "lrel_attachments_requests",
            f"cr like '{self.get_incident_id_by_ref_num(ref_num)}'",
            -1,
            ["attmnt"],
        )
        ids_xml = ET.fromstring(result).findall(".//AttrValue")
        ids = [id_xml.text for id_xml in ids_xml]
        attachments_list = []
        if ids:
            # get attachments data
            result = self._do_select(
                "attmnt",
                f"id in ({','.join(ids)})",
                -1,
                ["attmnt_name", "created_by.combo_name", "description", "created_dt"],
            )
            attachments = ET.fromstring(result.encode("utf-8")).findall(".//Attributes")
            for attachment in attachments:
                att_xml = attachment.findall(".//AttrValue")
                at = [at_xml.text for at_xml in att_xml]
                attachments_list.append(
                    {
                        "Name": at[0],
                        "CreatedBy": at[1],
                        "Description": at[2],
                        "CreatedOn": at[3],
                    }
                )
        return attachments_list

    def get_incident_properties(self, ref_num):
        """
        Get incident properties in CA Desk
        :param ref_num: {string}
        :return: {dict} properties data
        """
        # https://docops.ca.com/ca-service-management/14-1/en/reference/ca-service-desk-manager-reference-commands/
        # data-element-dictionary/request-property
        result = self._do_select(
            "cr_prp",
            f"owning_cr.ref_num like '{ref_num}'",
            -1,
            ["label", "value", "sample"],
        )
        properties = ET.fromstring(result.encode("utf-8")).findall(".//Attributes")
        properties_list = []
        for prop in properties:
            props_xml = prop.findall(".//AttrValue")
            p = [p_xml.text for p_xml in props_xml]
            properties_list.append({"Name": p[0], "Value": p[1], "Examples": p[2]})
        return properties_list

    def assign_incident_to_group(self, ref_num, group):
        """
        Assigns incident to a group.
        :param ref_num: incident's ref num {string}
        :param group: group to assign the incident to {string}
        :return: incident's ref num {string}
        """
        try:
            incident_id = self.get_incident_id_by_ref_num(ref_num)
            group_id = self.get_group_id_by_name(group.decode("utf-8"))

            if not group_id:
                raise CaManagerError(f"Bad Group name: {group}")

            result = self._client.service.updateObject(
                self._sid,
                incident_id,
                self._tf.ArrayOfString(["group", group_id]),
                self._tf.ArrayOfString(["ref_num"]),
            )
        except Exception as error:
            raise CaManagerError(f"Error in update_incident() {error}")

        updated_value = ET.fromstring(result.encode("utf-8")).find(".//AttrValue")

        if updated_value is not None:
            return updated_value.text

    def assign_incident_to_user(self, ref_num, username):
        """
        Assign an incident to a user.
        :param ref_num: incident number {string}
        :param username: username to assign the incident to. {string}
        :return: is_success {bool}
        """

        incident_id = self.get_incident_id_by_ref_num(ref_num)
        user_id = self.get_user_id_by_name(username)

        result = self._client.service.updateObject(
            self._sid,
            incident_id,
            self._tf.ArrayOfString(["assignee", user_id]),
            self._tf.ArrayOfString(["ref_num", "assignee"]),
        )

        updated_value = ET.fromstring(result).find(".//AttrValue")
        return updated_value is not None

    def get_status_id_by_status(self, status):
        """
        Get status system id by status name.
        :param status: status name {string}
        :return: status system id {string}
        """
        result = self._do_select(
            "in", f"status.sym like '{status.encode('utf-8')}'", 1, "status"
        )
        status_id_obj = ET.fromstring(result).find(".//AttrValue")

        if status_id_obj is not None:
            return status_id_obj.text
        raise CaManagerError(f'Status "{status.encode("utf-8")}" does not exist.')

    def get_tenant_id_by_tenant(self, tenant):
        """
        Get tenant system id by tenant name.
        :param tenant: tenant name {string}
        :return: tenant system id {string}
        """
        result = self._do_select(
            "in", f"tenant.name like '{tenant.encode('utf-8')}'", 1, "tenant"
        )
        tenant_id_obj = ET.fromstring(result).find(".//AttrValue")

        if tenant_id_obj is not None:
            return tenant_id_obj.text
        raise CaManagerError(f'tenant "{tenant.encode("utf-8")}" does not exist.')

    def change_ticket_status(self, ref_num, status):
        """
        Change the status of the ticket.
        :param ref_num: incident number {string}
        :param status: ticket status to change to. {string}
        :return: is_success {bool}
        """

        status_id = self.get_status_id_by_status(status)
        incident_id = self.get_incident_id_by_ref_num(ref_num)

        result = self._client.service.updateObject(
            self._sid,
            incident_id,
            self._tf.ArrayOfString(["status", status_id]),
            self._tf.ArrayOfString(["ref_num"]),
        )

        updated_value = ET.fromstring(result).find(".//AttrValue")
        return updated_value is not None

    def get_ticket_status(self, ticket_id, receive_status_id=False):
        """
        Get ticket status.
        :param ticket_id: {string} The ID of the target ticket.
        :param receive_status_id: {bool} Receive the ID of the status instead of the value.
        :return: {string} Ticket status/Ticket status ID.
        """
        if receive_status_id:
            result = self._do_select(
                "in", f"ref_num like '{ticket_id}'", 1, [TICKET_STATUS_ID_FIELD]
            )
        else:
            result = self._do_select(
                "in", f"ref_num like '{ticket_id}'", 1, [TICKET_STATUS_FIELD]
            )

        return ET.fromstring(result.encode("UTF-8")).find(".//AttrValue").text
