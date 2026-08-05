# Copyright 2026 Google LLC
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
