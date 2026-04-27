from __future__ import annotations
import ipaddress
from enum import Enum


class QueryOperatorEnum(Enum):
    AND = "and"
    OR = "or"


class OperatorEnum(Enum):
    EQ = "eq"
    GE = "ge"
    LE = "le"
    NE = "ne"


class Condition:
    def __init__(
        self,
        *,
        value,
        operator=None,
        field=None,
        join_values_with=None,
        quotes=True,
        value_formatter=None,
        use_parenthesis=True,
    ):
        self.is_valid = bool(field and value)
        self.field = field
        self.operator = operator if operator is not None else OperatorEnum.EQ.value
        self.value = value
        self.quotes = quotes
        self.use_parenthesis = use_parenthesis
        self.join_values_with = join_values_with or " "
        self.is_time_range = False

        if value_formatter:
            method, *args = (
                (value_formatter,)
                if isinstance(value_formatter, str)
                else value_formatter
            )
            getattr(self, method)(*args)

    def __str__(self):
        return f"{self.join_values_with.join(self._build_conditions())}"

    def _is_list(self):
        return isinstance(self.value, list)

    def _get_list_of_values(self):
        return self.value if self._is_list() else [self.value]

    def _build_conditions(self):
        value_wrapper = '"{}"' if self.quotes else "{}"
        return [
            f'({self.operator} {self.field or ""} {value_wrapper.format(value)})'
            for value in self._get_list_of_values()
        ]

    def ip_to_int(self):
        if self.is_valid:
            self.value = self.get_int_ips(self._get_list_of_values())

    def set_time_range(self):
        if self.is_valid:
            self.operator = ""
            self.quotes = self.use_parenthesis = False
            self.value = (
                "(timestamp {}) (timestamp {})".format(*self.value)
                if self.value
                else None
            )
            self.is_time_range = True

    @classmethod
    def ipv4_to(cls, value, _type):
        new_value = _type(ipaddress.IPv4Address(value))
        if _type == int:
            bite_str = f"{new_value:b}"
            return cls.binary_to_decimal(int(bite_str[2:]))
        return new_value

    @staticmethod
    def binary_to_decimal(binary):
        decimal, i, n = 0, 0, 0
        while binary != 0:
            dec = binary % 10
            decimal = decimal + dec * pow(2, i)
            binary = binary // 10
            i += 1
        return decimal

    @classmethod
    def get_int_ips(cls, ips):
        v4_ips, rest_ips = [], []

        for ip in (int(ip) if str(ip).isnumeric() else ip for ip in ips):
            (
                v4_ips
                if type(ipaddress.ip_address(ip)) is ipaddress.IPv4Address
                else rest_ips
            ).append(ip)

        v4_int_ips = [
            ip if isinstance(ip, int) else cls.ipv4_to(ip, int) for ip in v4_ips
        ]

        return v4_int_ips + rest_ips

    @classmethod
    def get_str_ips(cls, ips):
        return [cls.ipv4_to(ip, str) if str(ip).isnumeric() else ip for ip in ips]


class Query:
    def __init__(
        self, conditions, operator=None, join_conditions_with=None, use_parenthesis=True
    ):
        self.conditions = conditions
        self.operator = operator if operator is not None else QueryOperatorEnum.OR.value
        self.join_conditions_with = join_conditions_with or " "
        self.valid_conditions = [cnd for cnd in self.conditions if cnd.is_valid]
        self.is_valid = bool(
            self.valid_conditions
        )  # if query has last one valid condition
        self.use_parenthesis = use_parenthesis
        self.has_time_range = bool(
            [cnd for cnd in self.valid_conditions if cnd.is_time_range]
        )

        if not self.use_parenthesis:
            self.operator = ""

    def __str__(self):
        return self._get_query_str()

    def _get_query_str(self):
        conditions = self._build_query()
        query = f"{self.operator} {self.join_conditions_with.join(conditions)}"
        conditions_wrapper = "({})" if self.use_parenthesis else "{}"

        return conditions_wrapper.format(query)

    def _build_query(self):
        return [str(condition) for condition in self.conditions if condition.is_valid]


class QueryBuilder:
    def __init__(self, queries, operator=None, join_with=None, where=True):
        self.operator = (
            operator if operator is not None else QueryOperatorEnum.AND.value
        )
        self.join_with = join_with or " "
        self.queries = queries
        self.where = where
        self.valid_queries = [query for query in self.queries if query.is_valid]
        self.use_operator = len(self.valid_queries) > 1
        self.has_time_range = bool(
            [query for query in self.valid_queries if query.has_time_range]
        )
        self.only_time_range = self.has_time_range and len(self.valid_queries) == 1

    def __str__(self):
        return self._get_query_str() if self.valid_queries else ""

    def _build_queries(self):
        return [str(query) for query in self.valid_queries]

    def _get_query_str(self):
        query = self.join_with.join(self._build_queries())

        if self.use_operator:
            query = f"({self.operator} {query})"

        return f"({f'where {query}'})" if self.where else query
