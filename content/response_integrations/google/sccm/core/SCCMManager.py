# ============================================================================#
# title           :SCCMManager.py
# description     :This Module contain all SCCM operations functionality
# author          :avital@siemplify.co
# date            :28-01-2018
# python_version  :3.7
# libreries       :wmi
# requirments     : ports: 135, 445, 443 and RPC service on SCCM
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import wmi_client_wrapper as wmi
from .exceptions import SCCMManagerError, QueryException
from .constants import DOMAIN_USER
from .SCCMParser import SCCMParser
from pypika import Query, Table


class SCCMManager:

    def __init__(self, server_addr, domain, username, password):
        """
        Connect to a SCCM instance
        """
        self.parser = SCCMParser()
        self.sensitive_data_arr = [domain, username, password]

        try:
            # Connect to WMI instance with given credentials
            self.wmi = wmi.WmiClientWrapper(
                host=server_addr,
                username=DOMAIN_USER.format(domain=domain, username=username),
                password=password,
                namespace="ROOT\SMS",
            )

            site_namespace = self.wmi.query(
                "SELECT NamespacePath FROM SMS_ProviderLocation"
            )[0]["NamespacePath"]

            # Reconnect to site's namespace
            self.wmi = wmi.WmiClientWrapper(
                host=server_addr,
                username=DOMAIN_USER.format(domain=domain, username=username),
                password=password,
                namespace=site_namespace,
            )

        except Exception as error:
            raise SCCMManagerError(
                f"Unable to connect to {server_addr}: {error}", self.sensitive_data_arr
            )

    def get_login_history(self, username, limit):
        """
        Get login history of a user
        :param username: {str} The user whose login history will be retrieved.
        :param limit: {int} Maximum number of records to return.
        :return: {json} Login history of the user
        """
        login_data = self.wmi.query(self._build_login_history_query(username))
        login_history = []

        for login in login_data[:limit]:
            login_history.append(
                {
                    "Username": login["UniqueUserName"],
                    "LastLoggedIn": login["LastLoginTime"],
                    "LoginCount": login["LoginCount"],
                }
            )

        return login_history

    def get_computer_info(self, computer_name, siemplify):
        """
        Get info about a given computer
        :param computer_name: {str} The computer's name (hostname?)
        :return: {json} The info about the computer
        """
        query_table = Query.Table("SMS_R_System")
        query = (
            Query.from_(query_table)
            .select("*")
            .where(query_table.Name == f"{computer_name}")
        )
        siemplify.LOGGER.info(query.get_sql(quote_char=""))
        computer_query = self.wmi.query(query.get_sql(quote_char="").replace("'", '"'))

        # Should be list with the records
        if computer_query:
            # Take the first record
            return computer_query[0]

    def _build_login_history_query(self, username):
        """
        Build login history query.
        :param username: {str} The user about which the login history data is.
        :return: {str} The query for login history
        """
        query_table_second = Query.Table("SMS_R_User")
        query_table_first = Query.Table("SMS_UserMachineIntelligence")
        query = (
            Query.from_(query_table_first)
            .join(query_table_second)
            .on_field("UniqueUserName")
            .select(query_table_first.UniqueUserName)
            .select(query_table_first.LastLoginTime)
            .select(query_table_first.LoginCount)
            .select("ResourceName")
            .where(
                (
                    query_table_first.UniqueUserName.like(
                        f"{self._get_transformed_item(username)}"
                    )
                )
                | (
                    query_table_second.UserPrincipalName
                    == f"{self._get_transformed_item(username)}"
                )
                | (query_table_second.Mail == f"{self._get_transformed_item(username)}")
                | (
                    query_table_second.UserName
                    == f"{self._get_transformed_item(username)}"
                )
            )
        )
        return query.get_sql(quote_char="").replace("'", '"')

    def enrich_user(self, username):
        """
        Get enrichment data from SCCM by username
        :param username: {str} The username which is used to get enrichment data
        :return: {list} The SCCM data for username
        """
        result = self.wmi.query(self._build_enrichment_query_by_username(username))

        if result:
            return self.parser.build_user_enrichment_object(result)

    def enrich_host(self, hostname):
        """
        Get enrichment data from SCCM by hostname
        :param hostname: {str} The hostname which is used to get enrichment data
        :return: {list} The SCCM data for hostname
        """
        result = self.wmi.query(self._build_enrichment_query_by_hostname(hostname))

        if result:
            return self.parser.build_host_enrichment_object(result)

    def enrich_address(self, ip_address):
        """
        Get enrichment data from SCCM by IP address
        :param ip_address: {str} The IP address which is used to get enrichment data
        :return: {list} The SCCM data for IP address
        """
        result = self.wmi.query(self._build_enrichment_query_by_ip_address(ip_address))

        if result:
            return self.parser.build_address_enrichment_object(result)

    def _build_enrichment_query_by_username(self, username):
        """
        Build enrichment query by username.
        :param username: {str} The username which is used to get enrichment data
        :return: {str} The enrichment query by username
        """
        _query_table = Table("SMS_R_User")
        query = (
            Query.from_(_query_table)
            .select("*")
            .where(
                (
                    _query_table.UniqueUserName.like(
                        f"{self._get_transformed_item(username)}"
                    )
                )
                | (_query_table.Mail == f"{self._get_transformed_item(username)}")
                | (
                    _query_table.UserName.like(
                        f"{self._get_transformed_item(username)}"
                    )
                )
            )
        )
        return query.get_sql(quote_char="").replace("'", '"')

    def _build_enrichment_query_by_hostname(self, hostname):
        """
        Build enrichment query by hostname.
        :param hostname: {str} The hostname which is used to get enrichment data
        :return: {str} The enrichment query by hostname
        """
        _query_table = Table("SMS_R_System")
        query = (
            Query.from_("SMS_R_System")
            .select("*")
            .where(_query_table.Name == self._get_transformed_item(hostname))
        )
        return query.get_sql(quote_char="").replace("'", '"')

    def _build_enrichment_query_by_ip_address(self, ip_address):
        """
        Build enrichment query by IP address.
        :param ip_address: {str} The IP address which is used to get enrichment data
        :return: {str} The enrichment query by IP address
        """
        _query_table = Table("SMS_R_System")
        query = (
            Query.from_("SMS_R_System")
            .select("*")
            .where(_query_table.IpAddresses == self._get_transformed_item(ip_address))
        )
        return query.get_sql(quote_char="").replace("'", '"')

    def _get_transformed_item(self, item):
        """
        Transform special characters.
        :param item: {str} The item to transform
        :return: {str} The transformed item
        """
        return item.replace("\\", "\\\\").replace('"', '\\"')

    def run_wql_query(self, query):
        """
        Run WQL query in SCCM
        :param query: {str} The query to run in SCCM.
        :return: {list} The results of WQL query
        """
        try:
            return [
                self.parser.build_wql_query_result_object(result)
                for result in self.wmi.query(self._get_transformed_query(query))
            ]
        except Exception as e:
            raise QueryException(e, self.sensitive_data_arr)

    def _get_transformed_query(self, query):
        """
        Transform WQL query considering special characters
        :param query: {str} The query to transform.
        :return: {str} The transformed WQL query
        """
        return (
            query.replace("\\n", "")
            .replace("\\r", "")
            .replace("\\f", "")
            .replace("\\t", "")
        )
