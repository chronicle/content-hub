from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Catalog(BaseModel):
    def __init__(self, raw_data, title, type, num_records, site, id):
        super(Catalog, self).__init__(raw_data)
        self.title = title
        self.type = type
        self.num_records = num_records
        self.site = site
        self.id = id

    def to_table(self):
        table_data = {
            "Title": self.title,
            "Type": self.type,
            "Number of records": self.num_records,
            "Site": self.site,
        }

        return {key: value for key, value in table_data.items() if value}


class Breach(BaseModel):
    def __init__(self, raw_data, target_url, email, infected_time, sighting, severity, password):
        super(Breach, self).__init__(raw_data)
        self.target_url = target_url
        self.email = email
        self.infected_time = infected_time
        self.sighting = sighting
        self.severity = severity
        self.password = password

    def to_table(self):
        table_data = {
            "URL": self.target_url,
            "Email": self.email,
            "Infected Time": self.infected_time,
            "Sightings": self.sighting,
            "Severity": self.severity,
            "Password": (
                self.obfuscate_password(self.password) if self.password else self.password
            ),
        }

        return {key: value for key, value in table_data.items() if value is not None}

    def to_json(self):
        obfuscated_password = (
            self.obfuscate_password(self.password) if self.password else self.password
        )
        self.raw_data["password"] = obfuscated_password
        self.raw_data["password_plaintext"] = obfuscated_password
        return self.raw_data

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat({"was_breached": True})
        return add_prefix_to_dict(data, prefix) if prefix else data

    def obfuscate_password(self, password):
        obfuscated = ""
        for index in range(1, len(password) - 2):
            obfuscated += password[index].replace(password[index], "*")
        return password[0] + obfuscated + password[-2:]
