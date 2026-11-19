from __future__ import annotations
from zoho_desk.core.datamodels import *


class ZohoDeskParser:
    def build_results(self, raw_data, method, data_key="data"):
        return [
            getattr(self, method)(item_json)
            for item_json in self.extract_data_from_raw_data(
                raw_data, data_key=data_key
            )
        ]

    def extract_data_from_raw_data(self, raw_data, data_key="data"):
        return raw_data.get(data_key, [])

    @staticmethod
    def build_ticket_object(raw_data):
        return Ticket(
            raw_data=raw_data,
            id=raw_data.get("id"),
            subject=raw_data.get("subject"),
            description=raw_data.get("description"),
            ticket_number=raw_data.get("ticketNumber"),
            status=raw_data.get("status"),
            created_time=raw_data.get("createdTime"),
            resolution=raw_data.get("resolution"),
            email=raw_data.get("email"),
            first_name=raw_data.get("contact", {}).get("firstName"),
            last_name=raw_data.get("contact", {}).get("lastName"),
        )

    @staticmethod
    def build_comment_object(raw_data):
        return Comment(
            raw_data=raw_data,
            content=raw_data.get("content"),
            commented_time=raw_data.get("commentedTime"),
        )

    @staticmethod
    def build_department_object(raw_data):
        return Department(
            raw_data=raw_data, id=raw_data.get("id"), name=raw_data.get("name")
        )

    @staticmethod
    def build_contact_object(raw_data):
        return Contact(
            raw_data=raw_data, id=raw_data.get("id"), email=raw_data.get("email")
        )

    @staticmethod
    def build_product_object(raw_data):
        return Product(
            raw_data=raw_data, id=raw_data.get("id"), name=raw_data.get("email")
        )

    @staticmethod
    def build_agent_object(raw_data):
        return Agent(
            raw_data=raw_data,
            id=raw_data.get("id"),
            name=raw_data.get("name"),
            email=raw_data.get("emailId"),
        )

    @staticmethod
    def build_team_object(raw_data):
        return Team(raw_data=raw_data, id=raw_data.get("id"), name=raw_data.get("name"))
