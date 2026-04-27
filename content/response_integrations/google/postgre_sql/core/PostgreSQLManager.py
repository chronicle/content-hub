# ==============================================================================
# title           : PostgreSQLManager.py
# description     : This Module contain all PostgreSQL search functionality.
# author          : avital@siemplify.co
# date            : 29-04-18
# python_version  : 3.11
# libraries       : -
# requirements    : psycopg2
# product_version : 1.0
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import psycopg2
from functools import reduce


# =====================================
#              CLASSES                #
# =====================================
class PostgreSQLException(Exception):
    pass


class PostgreSQLManager:
    """
    PostgreSQL Manager
    """

    def __init__(self, username, password, server, database, port=5432):
        self.username = username
        self.password = password
        self.server = server
        self.database = database
        self.port = port

        # Connect to PostgreSQL
        self.conn = psycopg2.connect(
            f"dbname='{self.database}' user='{self.username}' host='{self.server}' password='{self.password}' port='{self.port}'"
        )

    def execute(self, query):
        """
        Execute a query on PostgresSQL database and get results.
        :param query: {str} SQL query like 'SELECT * FROM exampleDB'
        :return: {list} JSON like results
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            self.conn.commit()

            if cursor.description:
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
            raise PostgreSQLException(e)

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
