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

# ==============================================================================
# title           : MySQLManager.py
# description     : This Module contain all MySQL search functionality.
# author          : avital@siemplify.co
# date            : 29-04-18
# python_version  : 3.11
# libraries       : -
# requirements    : MySQLdb. Install MySQL connector from https://dev.mysql.com/downloads/connector/python/8.0.html
# product_version : 1.0
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
# import MySQLdb
from __future__ import annotations
import mysql.connector
from ..core import constants

from functools import reduce


# =====================================
#              CLASSES                #
# =====================================
class MySQLException(Exception):
    pass


class MySQLManager:
    """
    MySQL Manager
    """

    def __init__(self, username, password, server, database, port=3306):
        self.username = username
        self.password = password
        self.server = server
        self.database = database
        self.port = port

        # Connect to MySQL
        self.conn = mysql.connector.connect(
            host=self.server,
            user=self.username,
            password=self.password,
            database=self.database,
            port=self.port,
        )

    def execute(self, query):
        """
        Execute a query on MySQL database and get results.
        :param query: {str} SQL query like 'SELECT * FROM exampleDB'
        :return: {list} JSON like results
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(query)

            data = []

            if self._is_data_modifying_query(query):
                self.conn.commit()

            elif cursor.description:
                # Fetch column names
                columns = [column[0] for column in cursor.description]

                # Fetch rows
                rows = cursor.fetchall()

                # Construct results
                data = self.get_data(rows, columns)

            return data

        except Exception as e:
            # Query failed - rollback.
            self.conn.rollback()
            raise MySQLException(e)

        finally:
            cursor.close()

    def close(self):
        """
        Close the connection
        """
        self.conn.close()

    @staticmethod
    def get_data(rows, columns):
        """
        Converts list of rows to JSON like format.
        :param rows: {list} Data rows from PostgresSQL DB.
        :param columns: {list} Column names from PostgresSQL DB;
        :return: {list} JSON like formatted data from query.
        """
        data = []
        for row in rows:
            temp = {column: value for column, value in zip(columns, row)}
            data.append(temp)

        return data

    @staticmethod
    def construct_csv(results):
        """
        Constructs a csv from results
        :param results: The results to add to the csv (results are list of flat dicts)
        :return: {list} csv formatted list
        """
        csv_output = []
        headers = reduce(set.union, list(map(set, list(map(dict.keys, results)))))

        csv_output.append(",".join(map(str, headers)))

        for result in results:
            csv_output.append(
                ",".join(
                    [
                        s.replace(",", " ")
                        for s in map(
                            str,
                            [str(result.get(h, None)).encode("utf-8") for h in headers],
                        )
                    ]
                )
            )

        return csv_output

    @staticmethod
    def _is_data_modifying_query(query: str) -> bool:
        """
        Checks if a given SQL query is a data-modifying statement.
        """
        return query.strip().lower().startswith(constants.DATA_MODIFYING_STATEMENTS)
