from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self._get_enrichment_item(self.raw_data))
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_table(self):
        return [self.to_enrichment_data()]

    def _get_enrichment_item(self, data):
        """
        Get enrichment item based on latest agent time
        :return: {dict} The enrichment item
        """
        data.sort(
            key=lambda value: self._get_item_latest_agent_time(
                value.get("AgentTime", [])
            ),
            reverse=True,
        )
        return data[0]

    def _get_item_latest_agent_time(self, agent_times):
        """
        Get latest agent time
        :param agent_time: {list} The list of agent times
        :return: {str} The latest agent time
        """
        formatted_agent_times = [
            item.split(".")[0] for item in ",".join(agent_times).split(",")
        ]
        formatted_agent_times.sort(key=lambda value: value, reverse=True)
        return formatted_agent_times[0]


class User(BaseModel):
    """
    User data model represents user's data and it's used in actions that work with user
    """

    def __init__(self, raw_data=None):
        super(User, self).__init__(raw_data)


class Host(BaseModel):
    """
    Host data model represents host's data and it's used in actions that work with host
    """

    def __init__(self, raw_data=None):
        super(Host, self).__init__(raw_data)


class Address(BaseModel):
    """
    Address data model represents address's data and it's used in actions that work with address
    """

    def __init__(self, raw_data=None):
        super(Address, self).__init__(raw_data)


class WQLQueryResult(BaseModel):
    """
    WQLQueryResult data model represents WQL Query Result's data
    """

    def __init__(self, raw_data=None):
        super(WQLQueryResult, self).__init__(raw_data)

    def to_table(self):
        return dict_to_flat(self.raw_data)
