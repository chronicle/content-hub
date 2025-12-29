from __future__ import annotations

import json
import os
from enum import Enum

import pyaml
from cyberintegrations.exception import BadProtocolError, EmptyCredsError, EncryptionError
from cyberintegrations.utils import Validator as BaseValidator


class ConfigParser:
    def get_creds(self, config, key="creds"):
        # type: (dict, int | str) -> __get_enum_creds
        """Collect credentials from **YAML config**, filtered by **key**"""

        __creds = config.get(key, None)
        if __creds:
            return self.__get_enum_creds(**__creds)
        raise EmptyCredsError("Credentials not found")

    @staticmethod
    def __get_enum_creds(**kwargs):
        """
        Receive any kwargs to return Enum class with them.

        class Creds(Enum):
            API_KEY = kwargs.get("api_key", None)
            API_URL = kwargs.get("api_url", None)

            USERNAME = kwargs.get("username", None)
            PASSWORD = kwargs.get("password", None)

            IP = kwargs.get("ip", None)
            PORT = kwargs.get("port", None)

            BIG_DATA_LIMIT = kwargs.get("big_data_limit", None)
            DEFULT_LIMIT = kwargs.get("default_limit", None)

            DATA_DIR = kwargs.get("data_dir", None)
        """
        return Enum(
            "Creds",
            list(
                zip(
                    # make each key uppercase by 'map' function, which apply 'upper' method to keys
                    list(map(lambda x: x.upper(), kwargs.keys())),
                    kwargs.values(),
                )
            ),
            module=__name__,
        )

    @staticmethod
    def get_collection_default_date(config, collection):
        # type: (dict, str) -> str
        """Check **YAML config** by **collection** key and gather *default_date* field as str"""
        return str(config["collections"][collection]["default_date"])

    @staticmethod
    def get_collection_seq_update(config, collection):
        # type: (dict, dict) -> int
        """Check **YAML config** by **collection** key and gather *seqUpdate* field as int"""
        return int(config["collections"][collection]["default_date"])

    @staticmethod
    def get_enabled_collections(config):
        # type: (dict) -> list[str]
        """Check **YAML config** by *collection* key and gather enabled endpoints in list"""
        __collections = list()
        for collection in config["collections"].keys():
            if config["collections"][collection]["enable"]:
                __collections.append(collection)
        return __collections

    @staticmethod
    def get_disabled_collections(config):
        # type: (dict) -> list[str]
        """Check **YAML config** by *collection* key and gather enabled endpoints in list"""
        __collections = list()
        for collection in config["collections"].keys():
            if not config["collections"][collection]["enable"]:
                __collections.append(collection)
        return __collections


class FileHandler:
    """Singleton decorator for borg state logic"""

    # singleton state sharing
    _shared_borg_state = {}

    def __new__(cls, *args, **kwargs):
        obj = super(FileHandler, cls).__new__(cls, *args, **kwargs)
        obj.__dict__ = cls._shared_borg_state
        return obj

    def __init__(self):
        # self._magic = Magic(mime=True)  # For MIME types
        pass

    @staticmethod
    def is_exist(file):
        # type: (str) -> bool
        """Check if the **file** is exist"""
        return os.path.exists(file)

    @staticmethod
    def is_empty(file):
        # type: (str) -> bool
        """Check if the **file** is empty"""
        return True if os.stat(file).st_size == 0 else False

    # def is_yaml(self, file):
    #     # type: (str) -> bool
    #     """Check if the **file** is YAML"""
    #     return self.mime_type(file) == "text/plain" and \
    #            file.split(".")[-1] == "yaml" or \
    #            file.split(".")[-1] == "yml"

    # def is_json(self, file):
    #     # type: (str) -> bool
    #     """Check if the **file** is JSON"""
    #     return self.mime_type(file) == "application/json"

    # def mime_type(self, file):
    #     # type: (str) -> str
    #     """Return the **file** mime type"""
    #     return self._magic.from_file(file)

    def save_collection_info(self, config, collection, source="Adapter", **kwargs):
        # type: (str, str | list, str, dict) -> None
        """
        Update collection metadata at YAML config.

        :param config: path to the config
        :param collection: list of collections or single name
        :param source: **Adapter** for enabled collections only, else for all
        :param kwargs: args like {"seqUpdate": seq_update, "default_date": date}
        """

        if not self.is_exist(config):
            raise FileExistsError("File not exist!")

        # singleton logic
        in_progress = self._shared_borg_state.get("in_progress", False)
        if in_progress:
            while self._shared_borg_state.get("in_progress", False):
                pass
            self._in_progress = True

        # save data logic
        with open(config, "r") as f:
            data = pyaml.yaml.safe_load(f)

        if isinstance(collection, list):
            for col in collection:
                if source == "Adapter":
                    if data["collections"][col]["enable"]:
                        for k, v in kwargs[col].items():
                            data["collections"][col][k] = v
                else:
                    for k, v in kwargs[col].items():
                        data["collections"][col][k] = v
        else:
            if source == "Adapter":
                if data["collections"][collection]["enable"]:
                    for k, v in kwargs.items():
                        data["collections"][collection][k] = v
            else:
                for k, v in kwargs.items():
                    data["collections"][collection][k] = v

        with open(config, "w") as f:
            pyaml.yaml.dump(data, f, default_flow_style=False, sort_keys=True)

        # change status for next instance
        self._in_progress = False

    def read_yaml_config(self, config):
        # type: (str) -> dict[str, dict]
        """Read **YAML config** data"""
        if not self.is_exist(config):
            raise FileExistsError("File not exist!")
        # if not self.is_yaml(config):
        #     raise FileTypeError("File type not supported! Expected YML file!")

        # singleton logic
        in_progress = self._shared_borg_state.get("in_progress", False)
        if in_progress:
            while self._shared_borg_state.get("in_progress", False):
                pass
            self._in_progress = True

        with open(config, "r") as f:
            _config = pyaml.yaml.safe_load(f)

        # change status for next instance
        self._in_progress = False

        return _config

    def read_json_config(self, config):
        # type: (str) -> dict[str, dict]
        """Read **JSON config** data"""
        if not self.is_exist(config):
            raise FileExistsError("File not exist!")
        # if not self.is_json(config):
        #     raise FileTypeError("File type not supported! Expected JSON file!")

        # singleton logic
        in_progress = self._shared_borg_state.get("in_progress", False)
        if in_progress:
            while self._shared_borg_state.get("in_progress", False):
                pass
            self._in_progress = True

        with open(config, "r") as f:
            _config = json.load(f)

        # change status for next instance
        self._in_progress = False

        return _config

    def save_data_to_yaml_config(self, data, config):
        # type: (Any, str) -> None
        """Save **YAML config** data"""
        if not self.is_exist(config):
            raise FileExistsError("File not exist!")
        # if not self.is_yaml(config):
        #     raise FileTypeError("File type not supported! Expected YML file!")

        # singleton logic
        in_progress = self._shared_borg_state.get("in_progress", False)
        if in_progress:
            while self._shared_borg_state.get("in_progress", False):
                pass
            self._in_progress = True

        with open(config, "w") as f:
            pyaml.yaml.dump(data, f, default_flow_style=False, sort_keys=True)

        # change status for next instance
        self._in_progress = False

    def save_data_to_json_config(self, data, config):
        # type: (Any, str) -> None
        """Save **JSON config** data"""
        if not self.is_exist(config):
            raise FileExistsError("File not exist!")
        # if not self.is_json(config):
        #     raise FileTypeError("File type not supported! Expected JSON file!")

        # singleton logic
        in_progress = self._shared_borg_state.get("in_progress", False)
        if in_progress:
            while self._shared_borg_state.get("in_progress", False):
                pass
            self._in_progress = True

        with open(config, "w") as f:
            json.dump(data, f, indent=4)

        # change status for next instance
        self._in_progress = False


class ProxyConfigurator:
    @staticmethod
    def check_proxy_connection():
        pass

    @staticmethod
    def get_proxies(
        proxy_protocol=None,
        proxy_ip=None,
        proxy_port=None,
        proxy_username=None,
        proxy_password=None,
        encrypted_data_handler=None,
    ):
        # type: (str, str, str, str, str, Any) -> dict[str, str] | None
        """
        Method that returns proxies from given arguments. Only HTTP and HTTPS allowed.

            Return format:

            >>> {
            >>>     "http": "{protocol}://{username}:{password}@{ip}:{port}",
            >>>     "https": "{protocol}://{username}:{password}@{ip}:{port}"
            >>> }

        :param proxy_protocol: HTTP or HTTPS
        :param proxy_ip: 255.255.255.255 format
        :param proxy_port: 3128, 3129, ...
        :param proxy_username: Username
        :param proxy_password: Password parametr ignored for secure purpose
        :param encrypted_data_handler: Encryption object engine which is used to decrypt password
        :return: proxies
        """

        if not proxy_protocol or not proxy_ip or not proxy_port:
            return None

        protocol_allowed_list = ["http", "https"]
        proxy_protocol = proxy_protocol.lower()

        if proxy_protocol not in protocol_allowed_list:
            raise BadProtocolError(
                "Bad protocol used for proxy: {protocol}! Expected: {allowed}".format(
                    protocol=proxy_protocol, allowed=protocol_allowed_list
                )
            )

        if encrypted_data_handler:
            try:
                __proxy_password = encrypted_data_handler(label="proxy_password").decrypt()
            except EncryptionError:
                __proxy_password = None
        else:
            __proxy_password = proxy_password

        if proxy_username and __proxy_password:
            __proxy_dict = {
                "http": "{protocol}://{username}:{password}@{ip}:{port}".format(
                    protocol=proxy_protocol,
                    username=proxy_username,
                    password=__proxy_password,
                    ip=proxy_ip,
                    port=proxy_port,
                ),
                "https": "{protocol}://{username}:{password}@{ip}:{port}".format(
                    protocol=proxy_protocol,
                    username=proxy_username,
                    password=__proxy_password,
                    ip=proxy_ip,
                    port=proxy_port,
                ),
            }
            return __proxy_dict

        __proxy_dict = {
            "http": "{protocol}://{ip}:{port}".format(
                protocol=proxy_protocol, ip=proxy_ip, port=proxy_port
            ),
            "https": "{protocol}://{ip}:{port}".format(
                protocol=proxy_protocol, ip=proxy_ip, port=proxy_port
            ),
        }
        return __proxy_dict


class Validator(BaseValidator):
    @classmethod
    def validate_keys(cls, config):
        """
        Validates that each collection in the config contains non-empty keys with non-empty values.

        :param config: dict expected to contain collections and their keys
        :raises KeyError: if a collection is empty or missing
        :raises ValueError: if any key's value is empty
        :return: True if validation passes
        """
        __collections = config.keys()

        for collection in __collections:
            if not config[collection]:
                raise KeyError(f"Keys were not found in collection '{collection}'")

            for key in config[collection]:
                if not config[collection][key]:
                    raise ValueError(
                        f"A key '{key}' in collection '{collection}' has an empty value."
                    )

        return True

    @classmethod
    def validate_collections(cls, config):
        """
        Validates the 'collections' block in the provided config dictionary.
        Ensures each collection entry contains either 'default_date' or 'enable' key.

        :param config: dict expected to contain a 'collections' key
        :raises KeyError: if 'collections' is missing or required subkeys are missing
        :return: True if validation passes
        """
        __collections = config.get("collections", None)

        if not __collections:
            raise KeyError("A key 'collections' was not found in YAML file")

        for collection in __collections.keys():
            try:
                __collections[collection]["default_date"] or __collections[collection]["enable"]
            except KeyError as err:
                raise KeyError(f"A key {err} was not found in 'collection' dict")

        return True
