from __future__ import annotations
from urllib.parse import urljoin
import requests
from .constants import ENDPOINTS, EXECUTION_IN_PROGRESS, EXECUTION_FINISHED
from .UtilsManager import validate_response
from .SnowflakeParser import SnowflakeParser
import base64
import jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.serialization import PublicFormat
from cryptography.hazmat.backends import default_backend
import hashlib
from datetime import timedelta, timezone, datetime


class SnowflakeManager:
    def __init__(
        self,
        api_root,
        account,
        username,
        private_key_file,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API root of the Snowflake instance.
        :param account: {str} The name of the account configured with Snowflake.
        :param username: {str} Username used to access Snowflake.
        :param private_key_file: {str} Private key file that is used for authentication.
        :param verify_ssl: {bool} If enabled, verify the SSL certificate for the connection to the server is valid.
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.account = account
        self.username = username
        self.private_key_file = private_key_file
        self.logger = siemplify_logger
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = SnowflakeParser()

        self.jwt_token = self._generate_jwt_token()
        self.session.headers.update(
            {
                "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
                "Authorization": f"Bearer {self.jwt_token}",
            }
        )

    def _generate_jwt_token(self):
        """
        Generate JWT token
        :return: JWT token
        """
        file_content = base64.b64decode(self.private_key_file)
        private_key = load_pem_private_key(file_content, None, default_backend())

        # Get the raw bytes of the public key.
        public_key_raw = private_key.public_key().public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )

        # Get the sha256 hash of the raw bytes.
        sha256hash = hashlib.sha256()
        sha256hash.update(public_key_raw)

        # Base64-encode the value and prepend the prefix 'SHA256:'.
        public_key_fp = "SHA256:" + base64.b64encode(sha256hash.digest()).decode(
            "utf-8"
        )

        account = self.account

        # Get the account identifier without the region, cloud provider, or subdomain.
        if not ".global" in account:
            idx = account.find(".")
            if idx > 0:
                account = account[0:idx]
            else:
                # Handle the replication case.
                idx = account.find("-")
                if idx > 0:
                    account = account[0:idx]

        # Use uppercase for the account identifier and user name.
        account = account.upper()
        user = self.username.upper()
        qualified_username = account + "." + user

        # Get the current time in order to specify the time when the JWT was issued and the expiration time of the JWT.
        now = datetime.now(timezone.utc)

        # Specify the length of time during which the JWT will be valid. You can specify at most 1 hour.
        lifetime = timedelta(minutes=59)

        # Create the payload for the token.
        payload = {
            # Set the issuer to the fully qualified username concatenated with the public key fingerprint
            # (calculated in the previous step).
            "iss": qualified_username + "." + public_key_fp,
            # Set the subject to the fully qualified username.
            "sub": qualified_username,
            # Set the issue time to now.
            "iat": now,
            # Set the expiration time, based on the lifetime specified for this object.
            "exp": now + lifetime,
        }

        # Generate the JWT. private_key is the private key that you read from the private key file in the previous
        # step when you generated the public key fingerprint.
        encoding_algorithm = "RS256"
        token = jwt.encode(payload, key=private_key, algorithm=encoding_algorithm)

        # If you are using a version of PyJWT prior to 2.0, jwt.encode returns a byte string, rather than a string.
        # If the token is a byte string, convert it to a string.
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        return token

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param root_url: {str} The API root for the request
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity
        """
        request_url = self._get_full_url("ping")
        payload = {
            "statement": "SHOW TABLES LIMIT 1",
            "timeout": 60,
            "resultSetMetaData": {"format": "jsonv2"},
            "database": "SNOWFLAKE",
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response)

    def submit_query(self, query, database, schema, limit):
        """
        Submit query
        :param query: {str} The query to submit
        :param database: {str} The database to use
        :param schema: {str} Schema to use
        :param limit: {int} Results limit
        :return: {str} Query id
        """
        request_url = self._get_full_url("submit_query")
        payload = {
            "statement": query + f" LIMIT {limit}",
            "timeout": 300,
            "resultSetMetaData": {"format": "jsonv2"},
            "database": database,
        }
        if schema:
            payload["schema"] = schema

        response = self.session.post(request_url, json=payload)
        validate_response(response)

        return response.json().get("statementHandle")

    def build_query_string(
        self, fields_to_return, table, where_filter, sort_order, sort_field
    ):
        """
        Build the query to submit
        :param fields_to_return: {str} Csv of fields to return
        :param table: {str} Name of the table where to execute the query
        :param where_filter: {str} Where filter to add to the query
        :param sort_order: {str} Sort order
        :param sort_field: {str} Field to sort with
        :return: {str}
        """
        query_string = f"SELECT {fields_to_return}" if fields_to_return else "SELECT *"
        if table:
            query_string += f" FROM {table}"
        if where_filter:
            query_string += f" WHERE {where_filter}"
        if sort_field:
            query_string += f" ORDER BY {sort_field} {sort_order}"

        return query_string

    def get_data(self, query_id):
        """
        Get data
        :param query_id: {str} The query id
        :return: {tuple} Results list, Execution status
        """
        request_url = self._get_full_url("get_data", query_id=query_id)
        response = self.session.get(request_url)
        validate_response(response)

        if response.status_code == 202:
            return [], EXECUTION_IN_PROGRESS

        response_json = response.json()
        results = response_json.get("resultSetMetaData")
        data = response_json.get("data", [])

        if data:
            columns = [column.get("name") for column in results.get("rowType", [])]
            pretty_results = []
            for event in data:
                row_data = {}
                for i, column in enumerate(columns):
                    row_data[column] = event[i]
                pretty_results.append(row_data)

            return pretty_results, EXECUTION_FINISHED

        return [], EXECUTION_FINISHED
