# ==============================================================================
# title           : MongoDB.py
# description     : MongoDB to get data.
# author          : zivh@siemplify.co
# date            : 05-24-17
# python_version  : 2.7
# libraries       : -
# requirements    : pymongo
# product_version : 1.0
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================

from __future__ import annotations
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId

# =====================================
#              CLASSES                #
# =====================================


class MongoDBException(Exception):
    pass


class MongoDBManager:
    """
    The class defines some methods which help to get data from MongoDB.
    """

    def __init__(self, username, password, server, port, is_authenticate=False):
        """
        The method initialises required parameters for connection to MongoDB.
        :param username: {string} MongoDB login name;
        :param password: {string} password for login;
        :param server: IP or DNS name of MongoDB Server;
        :param port: {int};
        :param is_authenticate {boolean} True if using Username/Password, False if None
        """
        self.username = username
        self.password = password
        self.server = server
        self.port = port
        self.use_auth = is_authenticate

        # Connect to mongoDB
        self.client = MongoClient(self.server, self.port, connect=True)

    def test_connectivity(self):
        """
        Check if the connection is established or not.
        """
        try:
            # Forces a call.
            self.client.server_info()
            return True
        except ConnectionFailure as e:
            raise MongoDBException(f"Server not available. {e}")

    def validate_collection(self, collection_name, database_name):
        """
        Check if collection exist in specific database
        :param database_name: {String} database_name
        :param collection_name: {String} collection that exist in the specific database
        """
        database = self.client[database_name]
        collection_names = database.list_collection_names()
        if collection_name in collection_names:
            return True
        raise MongoDBException(
            f"Collection {collection_name} NOT exist in {database_name} database. Please try again."
        )

    def validate_database(self, database_name):
        """
        Check if specific database exist
        :param database_name: {String} database_name
        """
        databases = self.client.list_database_names()
        if database_name in databases:
            return True
        raise MongoDBException(f"Database {database_name} NOT exist. Please try again.")

    def execute_query(self, query, database_name, collection_name):
        """
        The method makes query on MongoDB and provide results.
        :param query: {Json} document - querying on specific elements. query={key:value}
        :param database_name: {String} database_name
        :param collection_name: {String} collection that exist in the specific database
        :return: data {list} list of matching documents{dicts}
        """
        try:
            data = []

            # Check if database exist
            self.validate_database(database_name)
            database = self.client[database_name]

            # Check if collection exist in db
            self.validate_collection(collection_name, database_name)
            collection = database[collection_name]

            # Check Authentication
            if self.use_auth:
                self.client = MongoClient(self.server, self.port, connect=True)

            # Query the database. Returns a Cursor instance
            results = collection.find(query)
            # doc = record
            for doc in results:
                for field_value in doc:
                    # ObjectId is not JSON serializable
                    if isinstance(doc[field_value], ObjectId):
                        doc[field_value] = str(doc[field_value])
                data.append(doc)

            return data

        except Exception as e:
            # Query failed - rollback.
            raise MongoDBException(e)

    def close_connection(self):
        """
        Close the connection
        """
        self.client.close()
