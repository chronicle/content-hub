class BaseModel:
    def __init__(self, raw_data: dict[str, any]):
        self.raw_data = raw_data

    def to_json(self) -> dict[str, any]:
        return self.raw_data


class SignalSciencesListItem(BaseModel):
    def __init__(self, raw_data: dict[str, any]):
        super().__init__(raw_data)
        self.id = raw_data.get("id")
        self.source = raw_data.get("source")
        self.note = raw_data.get("note")
        self.created_by = raw_data.get("createdBy")
        self.created = raw_data.get("created")
        self.expires = raw_data.get("expires")

    def to_json(self) -> dict[str, any]:
        return {
            "id": self.id,
            "source": self.source,
            "note": self.note,
            "createdBy": self.created_by,
            "created": self.created,
            "expires": self.expires,
        }


class AllowListItem(SignalSciencesListItem):
    """Represents an item in the Signal Sciences Allow List."""


class BlockListItem(SignalSciencesListItem):
    """Represents an item in the Signal Sciences Block List."""


class Site(BaseModel):
    def __init__(self, raw_data: dict[str, any]):
        super().__init__(raw_data)
        self.name = raw_data.get("name")
        self.display_name = raw_data.get("displayName")
        self.created = raw_data.get("created")
        self.agent_level = raw_data.get("agentLevel")

    def to_json(self) -> dict[str, any]:
        return {
            "name": self.name,
            "displayName": self.display_name,
            "created": self.created,
            "agentLevel": self.agent_level,
        }

    def to_table(self) -> dict[str, any]:
        return {
            "Name (API Name)": self.name,
            "Display Name": self.display_name,
            "Created": self.created,
            "Agent Level": self.agent_level,
        }
