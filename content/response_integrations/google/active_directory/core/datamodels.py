from __future__ import annotations
from TIPCommon import flat_dict_to_csv, dict_to_flat, add_prefix_to_dict


class BaseDataClass:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self, prefix=None):
        return flat_dict_to_csv(dict_to_flat(self.raw_data))

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_table(self):
        """
        Function that prepares the users's data to be used on the table
        :return {list} List containing dict of users's data
        """
        return [self.to_enrichment_data()]


class User(BaseDataClass):
    """
    User datamodel represents user's data and it's used in actions that work with user
    """

    def __init__(
        self, raw_data=None, name=None, telephone_num=None, manager=None, groups=[]
    ):
        super(User, self).__init__(raw_data)
        self.name = name
        self.telephone_num = telephone_num
        self.manager = manager
        self.groups = groups

    def to_csv(self, prefix=None):
        return flat_dict_to_csv(
            {"Manager Name": self.name, "Manager Phone": self.telephone_num}
        )


class Host(BaseDataClass):
    """
    Host datamodel represents host's data and it's used in actions that work with host
    """

    def __init__(self, raw_data=None):
        super(Host, self).__init__(raw_data)


class GroupMember(BaseDataClass):
    """
    Group member datamodel represents host's and User's data and it's used in actions that work with host and user
    """

    def __init__(
        self,
        raw_data=None,
        cn=None,
        name=None,
        display_name=None,
        distinguished_name=None,
    ):
        super(GroupMember, self).__init__(raw_data)
        self.cn = cn
        self.display_name = display_name
        self.distinguished_name = distinguished_name

    def to_json(self):
        return {
            "cn": self.cn,
            "displayName": self.display_name,
            "distinguishedName": self.distinguished_name,
        }
