# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from mp.core.data_models.abc import RepresentableEnum


class ActionProductCategories(BaseModel):
    enrich_ioc: Annotated[
        bool,
        Field(
            title="Enrich IOC (hash, filename, IP, domain, URL, CVE, Threat Actor, Campaign)",
            description=(
                "Returns reputation, prevalence, and threat intelligence"
                " (e.g., malware family, attribution) for the indicator."
            ),
        ),
    ] = False
    enrich_asset: Annotated[
        bool,
        Field(
            title="Enrich Asset (hostname, user or internal resource)",
            description=(
                "Returns contextual metadata (e.g., OS version, owner, department, MAC address)"
                " for a user or resource."
            ),
        ),
    ] = False
    update_alert: Annotated[
        bool,
        Field(
            title="Update Alert",
            description=(
                "Changes the status, severity, or assignee of the alert within the SecOps platform."
            ),
        ),
    ] = False
    add_alert_comment: Annotated[
        bool,
        Field(
            title="Add Alert Comment",
            description=(
                "Appends analyst notes or automated log entries to the alert's activity timeline."
            ),
        ),
    ] = False
    create_ticket: Annotated[
        bool,
        Field(
            title="Create Ticket",
            description=(
                "Generates a new record in an external ITSM (e.g., Jira, ServiceNow) and returns"
                " the Ticket ID."
            ),
        ),
    ] = False
    update_ticket: Annotated[
        bool,
        Field(
            title="Update Ticket",
            description=(
                "Synchronizes status, priority, or field changes from SecOps to the external"
                " ticketing system."
            ),
        ),
    ] = False
    add_ioc_to_blocklist: Annotated[
        bool,
        Field(
            title="Add IOC To Blocklist",
            description=(
                "Updates security controls (Firewall, EDR, Proxy) to prevent any future interaction"
                " with the IOC."
            ),
        ),
    ] = False
    remove_ioc_from_blocklist: Annotated[
        bool,
        Field(
            title="Remove IOC From Blocklist",
            description=(
                "Restores connectivity or execution rights for an indicator by removing it from"
                " restricted lists."
            ),
        ),
    ] = False
    add_ioc_to_allowlist: Annotated[
        bool,
        Field(
            title="Add IOC To Allowlist",
            description=(
                'Marks an indicator as "known good" to prevent future security alerts or false'
                " positives."
            ),
        ),
    ] = False
    remove_ioc_from_allowlist: Annotated[
        bool,
        Field(
            title="Remove IOC From Allowlist",
            description=(
                "Re-enables standard security monitoring and blocking for a previously trusted"
                " indicator."
            ),
        ),
    ] = False
    disable_identity: Annotated[
        bool,
        Field(
            title="Disable Identity (User, Account)",
            description=(
                "Revokes active sessions and prevents a user or service account from authenticating"
                " to the network."
            ),
        ),
    ] = False
    enable_identity: Annotated[
        bool,
        Field(
            title="Enable Identity (User, Account)",
            description=(
                "Restores authentication capabilities and system access for a previously disabled"
                " account."
            ),
        ),
    ] = False
    contain_host: Annotated[
        bool,
        Field(
            title="Contain Host",
            description=(
                "Isolates an endpoint from the network via EDR, allowing communication only with"
                " the management console."
            ),
        ),
    ] = False
    uncontain_host: Annotated[
        bool,
        Field(
            title="Uncontain Host",
            description=(
                "Removes network isolation and restores the endpoint's full communication"
                " capabilities."
            ),
        ),
    ] = False
    reset_identity_password: Annotated[
        bool,
        Field(
            title="Reset Identity Password (User, Account)",
            description=(
                "Invalidates the current credentials and triggers a password change or temporary"
                " password generation."
            ),
        ),
    ] = False
    update_identity: Annotated[
        bool,
        Field(
            title="Update Identity (User, Account)",
            description=(
                "Modifies account metadata, such as group memberships, permissions, or contact"
                " information."
            ),
        ),
    ] = False
    search_events: Annotated[
        bool,
        Field(
            title="Search Events",
            description=(
                "Returns a collection of historical logs or telemetry data matching specific search"
                " parameters."
            ),
        ),
    ] = False
    execute_command_on_the_host: Annotated[
        bool,
        Field(
            title="Execute Command on the Host",
            description=(
                "Runs a script or system command on a remote endpoint and returns the standard"
                " output (STDOUT)."
            ),
        ),
    ] = False
    download_file: Annotated[
        bool,
        Field(
            title="Download File",
            description=(
                "Retrieves a specific file from a remote host for local forensic analysis"
                " or sandboxing."
            ),
        ),
    ] = False
    send_email: Annotated[
        bool,
        Field(
            title="Send Email",
            description=(
                "Dispatches an outbound email notification or response to specified recipients."
            ),
        ),
    ] = False
    search_email: Annotated[
        bool,
        Field(
            title="Search Email",
            description=(
                "Identifies and lists emails across the mail server based on criteria like sender,"
                " subject, or attachment."
            ),
        ),
    ] = False
    delete_email: Annotated[
        bool,
        Field(
            title="Delete Email",
            description=(
                "Removes a specific email or thread from one or more user mailboxes"
                " (Purge/Withdraw)."
            ),
        ),
    ] = False
    update_email: Annotated[
        bool,
        Field(
            title="Update Email",
            description=(
                "Modifies the state of an email, such as moving it to quarantine, marking as read,"
                " or applying labels."
            ),
        ),
    ] = False
    submit_file: Annotated[
        bool,
        Field(
            title="Submit File",
            description=(
                "Uploads a file or sample to a sandbox or analysis engine"
                " (e.g., VirusTotal, Joe Sandbox) and returns a behavior report or threat score."
            ),
        ),
    ] = False


class ActionProductCategory(RepresentableEnum):
    ENRICH_IOC = "Enrich IOC (Indicator of Compromise)"
    ENRICH_ASSET = "Enrich Asset"
    UPDATE_ALERT = "Update Alert"
    ADD_ALERT_COMMENT = "Add Alert Comment"
    CREATE_TICKET = "Create Ticket"
    UPDATE_TICKET = "Update Ticket"
    ADD_IOC_TO_BLOCKLIST = "Add IOC to Blocklist"
    REMOVE_IOC_FROM_BLOCKLIST = "Remove IOC from Blocklist"
    ADD_IOC_TO_ALLOWLIST = "Add IOC to Allowlist"
    REMOVE_IOC_FROM_ALLOWLIST = "Remove IOC from Allowlist"
    DISABLE_IDENTITY = "Disable Identity (User, Account)"
    ENABLE_IDENTITY = "Enable Identity (User, Account)"
    CONTAIN_HOST = "Contain Host"
    UNCONTAIN_HOST = "Uncontain Host"
    RESET_IDENTITY_PASSWORD = "Reset Identity Password (User, Account)"  # noqa: S105
    UPDATE_IDENTITY = "Update Identity (User, Account)"
    SEARCH_EVENTS = "Search Events"
    EXECUTE_COMMAND_ON_THE_HOST = "Execute Command on the Host"
    DOWNLOAD_FILE = "Download File"
    SEND_EMAIL = "Send Email"
    SEARCH_EMAIL = "Search Email"
    DELETE_EMAIL = "Delete Email"
    UPDATE_EMAIL = "Update Email"
    SUBMIT_FILE = "Submit File"


PRODUCT_CATEGORY_TO_DEF_PRODUCT_CATEGORY: dict[str, ActionProductCategory] = {
    "enrich_ioc": ActionProductCategory.ENRICH_IOC,
    "enrich_asset": ActionProductCategory.ENRICH_ASSET,
    "update_alert": ActionProductCategory.UPDATE_ALERT,
    "add_alert_comment": ActionProductCategory.ADD_ALERT_COMMENT,
    "create_ticket": ActionProductCategory.CREATE_TICKET,
    "update_ticket": ActionProductCategory.UPDATE_TICKET,
    "add_ioc_to_blocklist": ActionProductCategory.ADD_IOC_TO_BLOCKLIST,
    "remove_ioc_from_blocklist": ActionProductCategory.REMOVE_IOC_FROM_BLOCKLIST,
    "add_ioc_to_allowlist": ActionProductCategory.ADD_IOC_TO_ALLOWLIST,
    "remove_ioc_from_allowlist": ActionProductCategory.REMOVE_IOC_FROM_ALLOWLIST,
    "disable_identity": ActionProductCategory.DISABLE_IDENTITY,
    "enable_identity": ActionProductCategory.ENABLE_IDENTITY,
    "contain_host": ActionProductCategory.CONTAIN_HOST,
    "uncontain_host": ActionProductCategory.UNCONTAIN_HOST,
    "reset_identity_password": ActionProductCategory.RESET_IDENTITY_PASSWORD,
    "update_identity": ActionProductCategory.UPDATE_IDENTITY,
    "search_events": ActionProductCategory.SEARCH_EVENTS,
    "execute_command_on_the_host": ActionProductCategory.EXECUTE_COMMAND_ON_THE_HOST,
    "download_file": ActionProductCategory.DOWNLOAD_FILE,
    "send_email": ActionProductCategory.SEND_EMAIL,
    "search_email": ActionProductCategory.SEARCH_EMAIL,
    "delete_email": ActionProductCategory.DELETE_EMAIL,
    "update_email": ActionProductCategory.UPDATE_EMAIL,
    "submit_file": ActionProductCategory.SUBMIT_FILE,
}
