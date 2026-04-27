from __future__ import annotations
from .datamodels import *


class MISPParser:
    @staticmethod
    def build_siemplify_save_response_obj(json_response):
        return SaveResponse(
            raw_data=json_response,
            is_saved=json_response.get("saved", False),
            error_msg=json_response.get("errors"),
            success_msg=json_response.get("success"),
        )

    @staticmethod
    def build_siemplify_event_obj(json_response):
        raw_data = json_response.get("Event", {})
        return Event(
            raw_data=raw_data,
            attributes=[
                MISPParser.build_siemplify_attribute_obj(attribute)
                for attribute in raw_data.get("Attribute", [])
            ],
            id=raw_data.get("id"),
            event_creator_email=raw_data.get("event_creator_email"),
            objects=raw_data.get("Object", []),
            published=raw_data.get("published"),
            info=raw_data.get("info"),
            timestamp=raw_data.get("timestamp"),
            related_events=[
                MISPParser.build_siemplify_event_obj(related_event)
                for related_event in raw_data.get("RelatedEvent", [])
            ],
            tags=[
                MISPParser.build_siemplify_tag_obj(tag)
                for tag in raw_data.get("Tag", [])
            ],
            galaxies=[
                MISPParser.build_siemplify_galaxy_obj(galaxy)
                for galaxy in raw_data.get("Galaxy", [])
            ],
            threat_level_id=raw_data.get("threat_level_id"),
            publish_timestamp=raw_data.get("publish_timestamp"),
            uuid=raw_data.get("uuid"),
            org_name=raw_data.get("Org", {}).get("name", ""),
            date=raw_data.get("date", ""),
            analysis=raw_data.get("analysis", ""),
            distribution=raw_data.get("distribution", ""),
        )

    @staticmethod
    def build_siemplify_api_message_obj(json_response):
        return ApiMessage(json_response, json_response.get("message"))

    @staticmethod
    def build_siemplify_api_sighting_obj(json_response):
        return Sighting(
            json_response,
            organisation_name=json_response.get("Organisation", {}).get("name"),
            **json_response.get("Sighting")
        )

    def build_attachment_object(self, raw_data):
        return MispAttachment(
            raw_data=raw_data,
            filename=raw_data.get("filename", ""),
            content=raw_data.get("base64", ""),
        )

    def build_siemplify_attribute_objs_from_list_of_json(
        self, json_response, limit=None
    ):
        attributes_json = json_response.get("response", {}).get("Attribute", [])
        if limit:
            attributes_json = attributes_json[:limit]
        return [
            self.build_siemplify_attribute_obj(attribute_json)
            for attribute_json in attributes_json
        ]

    @staticmethod
    def build_siemplify_attribute_obj(attribute_json):
        return Attribute(attribute_json, **attribute_json)

    @staticmethod
    def build_siemplify_galaxy_obj(galaxy_json):
        return Galaxy(galaxy_json, **galaxy_json)

    def build_list_of_siemplify_tag_objs(self, tags_json):
        tags_json = tags_json.get("Tag", [])
        return [self.build_siemplify_tag_obj(tag_json) for tag_json in tags_json]

    def build_list_of_misp_attachments(self, raw_json):
        raw_data = raw_json.get("result", [])
        return [self.build_attachment_object(item) for item in raw_data]

    def build_siemplify_event_objs_from_list_of_json(self, json_response):
        related_events_json = json_response.get("response", [])
        return [
            self.build_siemplify_event_obj(event_json)
            for event_json in related_events_json
        ]

    @staticmethod
    def build_siemplify_tag_obj(tag_json):
        return Tag(tag_json, tag_json.get("id"), tag_json.get("name"))

    @staticmethod
    def build_siemplify_object_template_obj(object_template_json):
        return ObjectTemplate(
            object_template_json,
            object_template_json.get("ObjectTemplate", {}).get("id"),
            object_template_json.get("ObjectTemplate", {}).get("name"),
        )

    def build_siemplify_misp_objects_from_events(self, event):
        return [
            self.build_siemplify_misp_obj(misp_object) for misp_object in event.objects
        ]

    def build_siemplify_misp_obj(self, obj_data):
        attributes = [
            self.build_siemplify_attribute_obj(attribute)
            for attribute in obj_data.get("Attribute", [])
        ]

        return MISPObject(
            raw_data={"Object": obj_data},
            id=obj_data.get("id"),
            name=obj_data.get("name"),
            description=obj_data.get("description"),
            uuid=obj_data.get("uuid"),
            event_id=obj_data.get("event_id"),
            comment=obj_data.get("comment"),
            timestamp=obj_data.get("timestamp"),
            attributes=attributes,
            meta_category=obj_data.get("meta-category"),
        )
