from __future__ import annotations
from .datamodels import User, Host, Address, WQLQueryResult


class SCCMParser:

    def build_user_enrichment_object(self, data):
        """
        Builds the user object based on raw data
        :param data: {list} User raw data
        :return {User} User object
        """
        return User(raw_data=data)

    def build_host_enrichment_object(self, data):
        """
        Builds the host object based on raw data
        :param data: {list} Host raw data
        :return {Host} Host object
        """
        return Host(raw_data=data)

    def build_address_enrichment_object(self, data):
        """
        Builds the address object based on raw data
        :param data: {list} Address raw data
        :return {Address} Address object
        """
        return Address(raw_data=data)

    def build_wql_query_result_object(self, data):
        """
        Builds the WQL query result object based on raw data
        :param data: {dict} WQL query result raw data
        :return {WQLQueryResult} WQLQueryResult object
        """
        return WQLQueryResult(raw_data=data)
