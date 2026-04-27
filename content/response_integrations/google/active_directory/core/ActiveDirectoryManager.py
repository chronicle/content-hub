# ==============================================================================
# title           :ActiveDirectoryManager.py
# description     :This Module contain all Active Directory operations functionality
# author          :org@siemplify.co
# date            :12-07-17
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
from ldap3 import (
    Server,
    Connection,
    SUBTREE,
    ALL_ATTRIBUTES,
    ALL_OPERATIONAL_ATTRIBUTES,
    MODIFY_REPLACE,
    MODIFY_ADD,
    MODIFY_DELETE,
    Tls,
)
import json
import ssl
import base64
from ldap3.core.exceptions import LDAPSocketOpenError
from .ActiveDirectoryCommon import ActiveDirectoryCommon
from .ActiveDirectoryParser import ActiveDirectoryParser

# =====================================
#             CONSTANTS               #
# =====================================
DISABLE_USER_VALUE = "514"
ENABLE_USER_VALUE = "512"
DISABLE_HOST_VALUE = "4098"
ENABLE_HOST_VALUE = "4096"
RESET_PASSWORD_VALUE = "0"


CA_CERTIFICATE_FILE_PATH = "cert.cer"

USER_QUERY_FIELDS = [
    "sAMAccountName",  # abc
    "userPrincipalName",  # abc@example.local
    "mail",  # abc@example.com
    "displayName",  # Name Surname
    "distinguishedName",  # 'CN=Name Surname,OU=R&D,OU=TLV,OU=example,DC=example,DC=LOCAL'
    "cn",  # Name Surname
]

HOST_QUERY_FIELDS = [
    "dNSHostName",  # LP-NAME-SURNAME.EXAMPLE.LOCAL
    "cn",  # LP-NAME-SURNAME
]

GROUP_QUERY_FIELDS = ["sAMAccountName"]  # Users / Guests / Administrators ...

OU_QUERY_FIELDS = ["name"]  # R&D ...

DEFAULT_USER_GROUP = "Domain Users"
SEARCH_ATTRIBUTES = [
    ALL_ATTRIBUTES,
    ALL_OPERATIONAL_ATTRIBUTES,
    "msDS-UserPasswordExpiryTimeComputed",
    "mail",
]

USER_ENTITY = "User"
HOST_ENTITY = "Host"

ENTITY_TYPE_QUERY_MAPPING = {USER_ENTITY: "user", HOST_ENTITY: "computer"}


# =====================================
#              CLASSES                #
# =====================================


class ActiveDirectoryManagerError(Exception):
    """
    General Exception for Active Directory manager
    """

    pass


class ActiveDirectoryNotFoundManagerError(Exception):
    """
    Not Found Exception for Active Directory manager
    """

    pass


class ActiveDirectoryNotExistPropertyError(Exception):
    """
    Exception for Active Directory not exist field error
    """

    pass


class ActiveDirectoryNotFoundGroupError(Exception):
    """
    Not Found Exception for Active Directory group
    """

    pass


class ActiveDirectoryNotFoundUserError(Exception):
    """
    Not Found Exception for Active Directory user
    """

    pass


class ActiveDirectoryCertificateError(Exception):
    """
    Exception for Active Directory certificate
    """

    pass


class ActiveDirectoryTimeoutError(Exception):
    """
    Timeout Error for Active Directory
    """

    pass


class ActiveDirectoryAccountAlreadyActive(Exception):
    """
    Account already active
    """

    pass


class ActiveDirectoryManager:
    """
    Responsible for all Active Directory operations functionality
    """

    def __init__(
        self,
        server_ip,
        domain,
        username,
        password,
        use_ssl=False,
        custom_query_fields=None,
        ca_certificate_file=None,
        siemplify_logger=None,
    ):

        self.siemplify_logger = siemplify_logger
        self.use_ssl = use_ssl
        self.tls = None
        self._verify_certificate_file(ca_certificate_file)
        self.server = Server(server_ip, use_ssl=self.use_ssl, tls=self.tls)
        # Create base DN from domain name
        self.domain = self._domain_base_dn(domain)
        self.parser = ActiveDirectoryParser(siemplify_logger)
        self.ad_common = ActiveDirectoryCommon(siemplify_logger)
        self.custom_query_fields = self.ad_common.process_custom_query_fields(
            custom_query_fields
        )
        try:
            self.conn = Connection(
                self.server, username, password, auto_bind=True, auto_encode=True
            )
        except LDAPSocketOpenError as e:
            if "socket ssl wrapping" in str(e):
                raise ActiveDirectoryCertificateError("Invalid certificate")
            raise ActiveDirectoryManagerError(f"Error: {e}")

        # Connect
        if self.use_ssl:
            self.conn.start_tls()
        self.conn.bind()

    def _verify_certificate_file(self, ca_certificate_file=None):
        if ca_certificate_file and self.use_ssl:
            self._save_certificate_file(ca_certificate_file)
            self.tls = self._build_tls()

    def _save_certificate_file(self, ca_certificate_file):
        try:
            file_content = base64.b64decode(ca_certificate_file).decode()
            with open(CA_CERTIFICATE_FILE_PATH, "w") as f:
                f.write(file_content)
        except Exception as e:
            raise ActiveDirectoryCertificateError(f"Certificate Error: {e}")

    def _build_tls(self):
        return Tls(ca_certs_file=CA_CERTIFICATE_FILE_PATH, validate=ssl.CERT_REQUIRED)

    def _domain_base_dn(self, domain):
        """
        Convert domain strong to active directory distinguish name
        :param domain: {str}
        :return: {str} in format "DC=siemplify, DC=local"
        """
        base_dn = ""
        for comp in domain.split("."):
            base_dn += f"DC={comp},"
        return base_dn[:-1]

    def _query_active_directory_by_filter(self, ldap_filter_string):
        """
        Query AD according to object's specific field
        :param ldap_filter_string: {str} The specific field to query on
        :return: {List[Entry]} ldap3 entry (false if no results were found)
        """
        try:
            result = self.conn.search(
                search_base=self.domain,
                search_filter=ldap_filter_string,
                search_scope=SUBTREE,
                attributes=SEARCH_ATTRIBUTES,
                get_operational_attributes=True,
            )

        except Exception as e:
            if "invalid attribute" in str(e):
                raise ActiveDirectoryNotExistPropertyError(f"Error: {e}")
            raise ActiveDirectoryManagerError(f"Error: {e}")
        # Check if there are any results
        if result and self.conn.entries:
            return self.conn.entries
        else:
            return False

    def _query_active_directory_with_paging(
        self, ldap_filter_string, size_limit=0, page_size=0, paged_cookie=None
    ):
        """
        Query AD according to object's specific field
        :param ldap_filter_string: {str} The specific field to query on
        :param size_limit {int} maximum number of entries returned by the search.
        :param page_size {int} The search will return at most the specified number of entries
        :param paged_cookie {str} an opaque string received in a paged paged search that must be sent back while requesting subsequent entries of the search result.
        :return: {List[Entry]} ldap3 entry (false if no results were found)
        """
        try:
            result = self.conn.search(
                search_base=self.domain,
                search_filter=ldap_filter_string,
                search_scope=SUBTREE,
                paged_size=page_size,
                paged_cookie=paged_cookie,
                size_limit=size_limit,
                attributes=SEARCH_ATTRIBUTES,
                get_operational_attributes=True,
            )
        except Exception as e:
            if "invalid attribute" in str(e):
                raise ActiveDirectoryNotExistPropertyError(f"Error: {e}")
            raise ActiveDirectoryManagerError(f"Error: {e}")
            # Check if there are any results
        if result and self.conn.entries:
            return self.conn.entries
        else:
            return False

    def _query_user_by_order(self, entity):
        """
        Search for user in AD using all attributes exists in class as fallback
        :param entity: {str} the entity to look for (user)
        :return: {object} ldap3 entry (false if no results were found)
        """
        entity = self.escape_ldap_special_chars(entity)

        # Iterate over predefine query fields and search the given entity by them
        # Try to fetch results using each one of those predefine fields

        # TODO: should we collect and array then return?
        for field in self.__get_custom_query_fields(USER_QUERY_FIELDS):
            ldap_query = f"(&(!(objectclass=computer))({field}={entity}))"
            results = self._query_active_directory_by_filter(ldap_query)
            # Once there are results for the query, return the results
            if results:
                return results[0]

    def escape_ldap_special_chars(self, ldap_filter):
        """
        Replace all special characters in ldap filter
        :param ldap_filter: {str}
        :return: {str}
        """
        return (
            ldap_filter.replace("\\", "\\5C")
            .replace("*", "\\2A")
            .replace("(", "\\28")
            .replace(")", "\\29")
            .replace("\000", "\\00")
        )

    def _query_group_by_order(self, group_name):
        """
        Search for group in AD using all attributes exists in class as fallback
        :param group_name: {str} the group name to look for
        :return: {object} ldap3 entry (false if no results were found)
        """
        # Iterate over predefine query fields and search the given group by them
        # Try to fetch results using each one of those predefine fields

        group_name = self.escape_ldap_special_chars(group_name)

        for field in GROUP_QUERY_FIELDS:
            ldap_query = f"(&(objectclass=group)({field}={group_name}))"
            results = self._query_active_directory_by_filter(ldap_query)
            # Once there are results for the query, return the results
            if results:
                return results[0]

    def _query_all_group_by_order(self, page_size=25, size_limit=0):
        """
        Search for all available groups in AD.
        :param page_size {int} The search will return at most the specified number of entries
        :param size_limit {int} maximum number of entries returned by the search.
        :return: {[ldap3.Entry]} List of Entries of group type.
        """
        groups = []

        ldap_query = "(&(objectclass=group))"
        group_entries, cookie = self.search_with_paging(
            ldap_query, page_size=page_size, size_limit=size_limit
        )
        groups.extend(group_entries)

        while cookie:
            group_entries, cookie = self.search_with_paging(
                ldap_query, page_size=page_size, size_limit=size_limit, cookie=cookie
            )
            if not group_entries or len(groups) >= size_limit:
                break

            groups.extend(group_entries)

        return groups[:size_limit] if size_limit else group_entries

    def _query_ou_by_order(self, ou_name):
        """
        Search for OU in AD using all attributes exists in class as fallback
        :param group_name: {str} the OU name to look for
        :return: {object} ldap3 entry (false if no results were found)
        """
        # Iterate over predefine query fields and search the given OU by them
        # Try to fetch results using each one of those predefine fields
        for field in OU_QUERY_FIELDS:
            ldap_query = f"(&(objectclass=organizationalUnit)({field}={ou_name}))"
            results = self._query_active_directory_by_filter(ldap_query)
            # Once there are results for the query, return the results
            if results:
                return results[0]

    def _query_host_by_order(self, entity):
        """
        Search for host in AD using all attributes exists in class as fallback
        :param entity: {str} the entity to look for (host)
        :return: {object} ldap3 entry (false if no results were found)
        """
        # Iterate over predefine query fields and search the given entity by them
        # Try to fetch results using each one of those predefine fields
        for field in self.__get_custom_query_fields(HOST_QUERY_FIELDS):
            ldap_query = f"(&(objectclass=computer)({field}={entity}))"
            results = self._query_active_directory_by_filter(ldap_query)
            # Once there are results for the query, return the results
            if results:
                return results[0]

    def _format_json_response(self, json_response):
        """
        Convert json results response to dict
        :param json_response: {str} json result
        :return: {dict}
        """
        dict_response = json.loads(json_response)
        return dict_response["attributes"]

    def test_connectivity(self, username_for_check):
        """
        Test connection to sever
        :return: {bool}
        """
        try:
            # Try fetching data on user in order to validate given Domain name
            results = self._query_user_by_order(username_for_check)
            if results:
                return True
            return False
        # Exception raises in case Domain name is invalid
        except LDAPSocketOpenError as e:
            raise ActiveDirectoryManagerError(
                f"Domain name-{self.domain} is wrong, error-{e}"
            )

    def disable_account(self, user):
        """
        Disable user account in Active Directory
        :return: {bool}
        """
        result = self._query_user_by_order(user)
        if not result:
            return False
        # Extract user DN
        user_dn = result.distinguishedName.value

        disabled_account = result.userAccountcontrol.value | int("0b10", 2)

        # Ldap3 modification request
        return self.conn.modify(
            user_dn, {"userAccountcontrol": [(MODIFY_REPLACE, [disabled_account])]}
        )

    def enable_account(self, user):
        """
        Enable user account in Active Directory
        :return: {bool}
        """
        result = self._query_user_by_order(user)
        if not result:
            raise ActiveDirectoryManagerError(f"User {user} not found.")

        # Extract user DN
        user_dn = result.distinguishedName.value
        account_enabled = not result.userAccountcontrol.value & int("0b10", 2)
        if account_enabled:
            raise ActiveDirectoryAccountAlreadyActive("User {user} is already active")
        try:
            # Ldap3 modification request
            enabled_account = result.userAccountcontrol.value & ~int("0b10", 2)
            self.conn.modify(
                user_dn, {"userAccountcontrol": [(MODIFY_REPLACE, [enabled_account])]}
            )
        except Exception as e:
            raise ActiveDirectoryManagerError(
                f"Something went wrong while enabling {user}'s account: {e}"
            )
        return True

    def disable_computer(self, host):
        """
        Disable computer account in Active Directory
        :return: {bool} True if successful, exception otherwise
        """
        result = self._query_host_by_order(host)
        if not result:
            raise ActiveDirectoryNotFoundManagerError(f"Computer {host} not found.")
        try:
            # Extract host DN
            # Ldap3 modification request
            host_dn = result.distinguishedName.value
            self.conn.modify(
                host_dn,
                {"userAccountcontrol": [(MODIFY_REPLACE, [DISABLE_HOST_VALUE])]},
            )
        except Exception as e:
            raise ActiveDirectoryManagerError(
                f"Something went wrong while disabling {host}'s computer account: {e}"
            )
        return True

    def enable_computer(self, host):
        """
        Enable computer account in Active Directory
        :return: {bool} True if successful, exception otherwise
        """
        result = self._query_host_by_order(host)
        if not result:
            raise ActiveDirectoryNotFoundManagerError(f"Computer {host} not found.")
        try:
            # Extract host DN
            # Ldap3 modification request
            host_dn = result.distinguishedName.value
            self.conn.modify(
                host_dn, {"userAccountcontrol": [(MODIFY_REPLACE, [ENABLE_HOST_VALUE])]}
            )
        except Exception as e:
            raise ActiveDirectoryManagerError(
                f"Something went wrong while enabling {host}'s computer account: {e}"
            )
        return True

    def force_password_update(self, user):
        """
        Force user to change password on the next logon
        :return: {bool}
        """
        result = self._query_user_by_order(user)
        if not result:
            return False
        # Extract user DN
        user_dn = result.distinguishedName.value
        # Ldap3 modification request
        return self.conn.modify(
            user_dn, {"pwdLastSet": [(MODIFY_REPLACE, [RESET_PASSWORD_VALUE])]}
        )

    def release_locked_account(self, user):
        """
        Release locked user in Active Directory
        :return: {bool}
        """
        # Same as enable account method
        return self.unlock_account(user)

    def unlock_account(self, user):
        result = self._query_user_by_order(user)
        if not result:
            raise ActiveDirectoryManagerError(f"User {user} not found.")
        try:
            # Extract user DN
            # Ldap3 modification request
            user_dn = result.distinguishedName.value
            self.conn.modify(user_dn, changes={"lockoutTime": [(MODIFY_REPLACE, [0])]})
        except Exception as e:
            raise ActiveDirectoryManagerError(
                f"Something went wrong while enabling {user}'s account: {e}"
            )
        return True, self.conn.result.get("description")

    def enrich_user(self, user):
        """
        Get all user object attributes details from Active Directory
        :param user:
        :return: flat dict of all object properties ex - {'logonCount': 17, 'lastLogon': 2017-11-23 08:27:17.676741+00:00} etc.
        """
        result = self._query_user_by_order(user)
        if result:
            # make dict(json) from ldap Entity
            data = self._format_json_response(result.entry_to_json())
            return self.parser.build_siemplify_user_object(
                data, groups=list(self.load_nested_groups(data, set()))
            )
        return None

    def enrich_host(self, host):
        """
        Get all host object attributes details from Active Directory
        :param host:
        :return: flat dict of all object properties ex - {'logonCount': 17, 'lastLogon': 2017-11-23 08:27:17.676741+00:00} etc.
        """
        result = self._query_host_by_order(host)
        if result:
            # make dict(json) from ldap Entity
            data = self._format_json_response(result.entry_to_json())
            return self.parser.build_siemplify_host_object(data)
        return None

    def enrich_manager_details(self, user):
        """
        Get all user's manager object attributes details from Active Directory
        :param user:
        :return: ({bool}, {dict}) - Tuple - True if user exists, otherwise False and A flat dict of all object properties ex - {'logonCount': 17, 'lastLogon': 2017-11-2308:27:17.676741+00:00} etc.
            If manager does not exist, or user entity is invalid/missing an empty dictionary will be returned as manager's data.
        """
        user_data = self.enrich_user(user)
        if user_data:
            manager = user_data.manager
            if manager:
                manager_data = self.enrich_user(manager[0])
                return True, manager_data
            else:
                return True, {}
        return False, {}

    def list_user_groups(self, user, raise_if_user_is_invalid=False):
        """
        Get all groups user is assign to in Active Directory
        :param user: {str} User to list user groups for
        :param raise_if_user_is_invalid: {bool} True if to raise an ActiveDirectoryNotFoundManagerError exception in case the user does not
        exist, otherwise False
        :return: {list of str} list of groups names (false if no results were found)
        """
        user_data = self.enrich_user(user)
        if not user_data:
            if raise_if_user_is_invalid:
                raise ActiveDirectoryNotFoundManagerError(f"User {user} not found.")
            return []
        # Add the default group of all active directory users
        return user_data.groups + [DEFAULT_USER_GROUP]

    def __get_custom_query_fields(self, default_query_fields=[]):
        return [
            field
            for field in self.custom_query_fields
            if field not in default_query_fields
        ] + default_query_fields

    def search_with_paging(self, search_filter, page_size=0, cookie=None, size_limit=0):
        """
        :param search_filter: {str} The specific field to query on
        :param page_size {int} The search will return at most the specified number of entries
        :param size_limit {int} maximum number of entries returned by the search.
        :param cookie {str} an opaque string received in a paged paged search that must be sent back while requesting subsequent entries of the search result.
        :return: {list of flat objects}
        """
        total_entries = 0
        entities = []
        if size_limit:
            page_size = min(page_size, size_limit)

        while True:
            entries: List[Entry] = self._query_active_directory_with_paging(
                search_filter,
                page_size=page_size,
                size_limit=size_limit,
                paged_cookie=cookie,
            )

            if not entries:
                break

            cookie = self.conn.result["controls"]["1.2.840.113556.1.4.319"]["value"][
                "cookie"
            ]
            total_entries += len(entries)
            entities.extend(
                [self._format_json_response(entry.entry_to_json()) for entry in entries]
            )
            if (page_size == total_entries) or (not cookie):
                break

        return entities, cookie

    def list_user_group_members(
        self,
        page_size=0,
        size_limit=0,
        entity_type=None,
        cookie=None,
        is_nested_search=False,
        member_of=None,
    ):
        """
        Get all groups user is assign to in Active Directory
        :param page_size {num} max count of entities per page
        :param size_limit {int} maximum number of entries returned by the search.
        :param cookie {str} an opaque string received in a paged paged search that must be sent back while requesting subsequent entries of the search result.
        :param is_nested_search {bool} group name
        :param member_of {str} group name
        :param entity_type {'User' | 'Host'}
        :return: {list of strings} list of groups names (false if no results were found), cookie {str} (None if no more available pages)
        """
        nested_search = ":1.2.840.113556.1.4.1941:" if is_nested_search else ""
        ldap_query = f"(&(objectCategory={ENTITY_TYPE_QUERY_MAPPING[entity_type]})(memberOf{nested_search}={member_of}))"

        entities, cookie = self.search_with_paging(
            ldap_query, page_size=page_size, size_limit=size_limit, cookie=cookie
        )
        return self.parser.build_siemplify_group_members(entities), cookie

    def get_group_distinguished_name(self, group_name):
        """
        Load nested groups from parent_json. This is recursive action.
        :param group_name {str} Name of the group
        :return: {str} Group distinguished name.
        """
        group = self._query_group_by_order(group_name)
        if not group:
            raise ActiveDirectoryNotFoundGroupError(
                f"Could not get Active Directory group {group_name} members. Group does not exist."
            )
        return group.distinguishedName

    def list_groups(self, page_size=0, size_limit=0):
        """
        List all available groups from AD.
        :return: {[ldap3.Entry]} List of Entries of group type.
        """
        groups = self._query_all_group_by_order(
            page_size=page_size, size_limit=size_limit
        )
        if not groups:
            raise ActiveDirectoryNotFoundGroupError(
                "Could not get Active Directory groups. There are no groups exists"
            )

        return groups

    def load_nested_groups(self, parent_json, groups):
        """
        Load nested groups from parent_json. This is recursive action.
        :param parent_json {json} JSON which contains groups
        :param groups: {set} Set of groups to merge with loaded groups
        :return: {set} Final set of merged groups.
        """
        group_array = self.parser.get_user_groups(parent_json)
        for group_name in group_array:
            # If group name is already in groups list - means that we have a loop in the groups hierarchy
            # So instead of querying it again, ignore it to avoid an endless loop
            # According to lab ops team, group name is unique so this is
            # BEWARE - this is still a recursion, so even though it is highly unlikely to have more than X100
            # group hierarchy levels, this is still a possibility. So if we encounter a case in which we
            # get a StackOverflow exception because of too many levels, we can add a level counter and limit the
            # recursion depth to upto some limit.
            if group_name not in groups:
                group = self._query_group_by_order(group_name)
                if group:
                    groups.add(group_name)
                    group_json = self._format_json_response(group.entry_to_json())
                    if group_json:
                        groups = self.load_nested_groups(group_json, groups)
        return groups

    def add_user_to_group(self, user_name, group_name):
        """
        Add a user to a group
        :param user_name {str} The name of the user to add to the group
        :param group_name: {str} The name of the new user's group
        :return: {bool} True if successful, False otherwise.
        """
        user = self._query_user_by_order(user_name)
        group = self._query_group_by_order(group_name)

        if not user:
            raise ActiveDirectoryNotFoundUserError(f"User {user_name} not found.")

        if not group:
            raise ActiveDirectoryNotFoundGroupError(f"Group {group_name} not found.")

        self.conn.modify(group.entry_dn, {"member": [(MODIFY_ADD, [user.entry_dn])]})

        return self.conn.result

    def remove_user_from_group(self, user, group_name):
        """
        Remove a user from a group
        :param group_name: {str} The name of the user's group
        :return: {bool} True if successful, False otherwise.
        """
        group = self._query_group_by_order(group_name)

        if not group:
            raise ActiveDirectoryNotFoundGroupError(f"Group {group_name} not found.")

        self.conn.modify(group.entry_dn, {"member": [(MODIFY_DELETE, [user.entry_dn])]})

        return self.conn.result

    def get_user(self, user_name):
        """
        Get User from ActiveDirectory
        :param user_name: The username of the user to fetch
        :return: {datamodels.User} User data model
        """
        user = self._query_user_by_order(user_name)

        if not user:
            raise ActiveDirectoryNotFoundUserError(f"User {user_name} not found.")

        return user

    def set_user_password(self, user_name, password):
        """
        Set password for a given user
        :param user_name: {str} The name of the user to set the password of
        :param password: {str} The password to set
        :return: {bool} True if successful, exception otherwise.
        """
        user = self._query_user_by_order(user_name)

        if not user:
            raise ActiveDirectoryManagerError(f"User {user_name} not found.")
        try:
            return self.conn.extend.microsoft.modify_password(user.entry_dn, password)
        except Exception as e:
            raise ActiveDirectoryManagerError(
                f"Something went wrong while updating {user_name}'s password: {e}"
            )
        return False

    def change_user_ou(self, user_name, ou_name):
        """
        Change user's OU
        :param user_name {str} The name of the user to change
        :param ou_name: {str} The name of the new user's OU
        :return: {bool} True if successful, False otherwise.
        """
        user = self._query_user_by_order(user_name)
        ou = self._query_ou_by_order(ou_name)

        if not user:
            raise ActiveDirectoryManagerError(f"User {user_name} not found.")
        if not ou:
            raise ActiveDirectoryManagerError(f"OU {ou_name} not found.")

        # Change the OU
        return self.conn.modify_dn(
            user.entry_dn, f"CN={user.cn.value}", new_superior=ou.entry_dn
        )

    def change_host_ou(self, host_name, ou_name):
        """
        Change host's OU
        :param host_name {str} The name of the host to change
        :param ou_name: {str} The name of the new user's OU
        :return: {bool} True if successful, False otherwise.
        """
        host = self._query_host_by_order(host_name)
        ou = self._query_ou_by_order(ou_name)
        if not host:
            raise ActiveDirectoryManagerError(f"Host {host} not found.")
        if not ou:
            raise ActiveDirectoryManagerError(f"Host {host} not found.")
        try:
            self.conn.modify_dn(
                host.entry_dn, f"CN={host.cn.value}", new_superior=ou.entry_dn
            )
        except Exception as e:
            raise ActiveDirectoryManagerError(
                f"Something went wrong while updating {host_name}'s OU: {e}"
            )
        return True

    def update_user(self, user_name, attribute_name, value):
        """
        Update a user's attribute
        :param user_name: {str} The username to update
        :param attribute_name: {str} The attribute name to update
        :param value: {str} The value to set
        :return: {bool} True if successful, exception otherwise
        """
        user = self._query_user_by_order(user_name)

        if not user:
            raise ActiveDirectoryNotFoundManagerError(f"User {user_name} not found.")
        try:
            result = self.conn.modify(
                user.entry_dn, {attribute_name: [(MODIFY_REPLACE, value)]}
            )
            if not result:
                raise ActiveDirectoryNotExistPropertyError
            return result
        except ActiveDirectoryNotExistPropertyError:
            raise
        except Exception as e:
            raise ActiveDirectoryManagerError(
                f"Something went wrong while updating {user_name}'s {attribute_name} attribute value: {e}"
            )

    def update_host(self, host_name, attribute_name, value):
        """
        Update a host's attribute
        :param host_name: {str} The host to update
        :param attribute_name: {str} The attribute name to update
        :param value: {str} The value to set
        :return: {bool} True if successful, exception otherwise
        """
        host = self._query_host_by_order(host_name)

        if not host:
            raise ActiveDirectoryNotFoundManagerError(f"Host {host} not found.")
        try:
            result = self.conn.modify(
                host.entry_dn, {attribute_name: [(MODIFY_REPLACE, value)]}
            )
            if not result:
                raise ActiveDirectoryNotExistPropertyError
            return result
        except ActiveDirectoryNotExistPropertyError:
            raise
        except Exception as e:
            raise ActiveDirectoryManagerError(
                f"Something went wrong while updating {host_name}'s {attribute_name} attribute value: {e}"
            )
