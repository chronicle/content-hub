# ==============================================================================
# title           : RedisManager.py
# description     : Redis to get data.
# author          : zivh@siemplify.co
# date            : 06-19-17
# python_version  : 2.7
# libraries       : -
# requirements    : Redis
# product_version : 1.0
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import redis

# =====================================
#              CLASSES                #
# =====================================


class RedisException(Exception):
    pass


class RedisManager:
    """
    The class defines some methods which help to get data from Redis.
    By default, all responses are returned as bytes in Python 3 and str in Python 2.
    The user is responsible for decoding to Python 3 strings or Python 2 unicode objects.
    """

    def __init__(self, server, port, db_index=0):
        """
        The method initialises required parameters for connection to Redis.
        :param server: IP or DNS name of Redis Server;
        :param port: {int};
        :param db_index: {int} The database to where the data is written can be selected by specifying the index of the database, which is a number.
        """
        # Connect to redis by creating a StrictRedis instance
        self.redis_client = redis.StrictRedis(
            host=server, port=port, db=db_index, decode_responses=True
        )

    def test_connectivity(self):
        """
        Ping the Redis server
        """
        try:
            # Forces a call.
            return self.redis_client.ping()
        except RedisException as e:
            raise RedisException(f"Server not available. {e}")

    def set_key(self, key_name, value):
        """
        Set some string value in redis key.
        If the key already holds a value, it is overwritten, regardless of its type.
        :param key_name: {str} existing key name or new one
        :param value: {any type: str, int, dict, list, etc.}
        :return: {boolean} True/False
        """
        try:
            return self.redis_client.set(key_name, value)

        except Exception as e:
            raise RedisException(f"Couldn't set value in {key_name}. Error:{e}")

    def get_key(self, key_name):
        """
        Get the key value
        :param key_name: {str} existing key name or new one
        :return: Return the value at key name, or None if the key doesnt exist {unicode}
        """
        try:
            return self.redis_client.get(key_name)

        except Exception as e:
            raise RedisException(e)

    def add_to_list(self, list_name, value):
        """
        The LPUSH command adds a value to the head of a Redis list.
        If the list not exist, a new one is created.
        :param list_name: {str}
        :param value: {any type: str, int, dict, list, etc.}
        :return: {long} the index of the value in the list.
        """
        try:
            return self.redis_client.lpush(list_name, value)
        except Exception as e:
            raise RedisException(e)

    def get_list(self, list_name):
        """
        LINDEX command returns a value of an element from a Redis list as defined by the index.
        :param list_name: {str}
        :return: {list} list with all the values
        """
        redis_list = []
        for i in range(0, self.redis_client.llen(list_name)):
            redis_list.append(self.redis_client.lindex(list_name, i))
        return redis_list
