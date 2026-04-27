from __future__ import annotations
import base64
import os
import arrow
import requests
from TIPCommon import SiemplifySession
from .MISPParser import MISPParser
from .constants import ATTRIBUTE_SEARCH_MAPPER, PROVIDED_EVENT
from .datamodels import SIGHTING_LEVELS
from .exceptions import (
    MISPManagerError,
    MISPManagerObjectNotFoundError,
    MISPManagerAttributeNotFoundError,
    MISPManagerTagNotFoundError,
    MISPManagerEventIdNotFoundError,
    MISPManagerCreateEventError,
    MISPCertificateError,
)


# ============================== CONSTANTS ===================================== #

HEADERS = {
    "Authorization": None,
    "Accept": "application/json",
    "Content-Type": "application/json",
}

URL = "url"
HOSTNAME = "hostname"
DOMAIN = "domain"
SRC_IP = "ip-src"
DST_IP = "ip-dst"
FILENAME = "filename"
EMAIL_SUBJECT = "email-subject"
THREAT_CAMPAIGN = "campaign-name"
THREAT_ACTOR = "threat-actor"
PHONE_NUMBER = "phone-number"
USER = "target-user"


NOT_FOUND_STATUS = 404
FORBIDDEN_STATUS = 403

CA_CERTIFICATE_FILE_PATH = "cert.cer"


API_ENDPOINTS = {
    "add_object": "{}/objects/add/{}/{}",
    "list_sighting": "{}/sightings/listSightings/{}/attribute/",
    "edit_attribute": "{}/attributes/editField/{}",
    "add_sighting": "{}/sightings/add",
    "remove_sighting": "{}/sightings/add",
    "add_tag": "{}/events/addTag/",
    "remove_tag": "{}/events/removeTag/",
    "update_event": "{}/events/edit/{}",
    "delete_event": "{}/events/delete/{}",
    "unpublish_event": "{}/events/unpublish/{}",
    "publish_event": "{}/events/publish/{}",
    "search_attributes": "{}/attributes/restSearch",
    "attach_tag_to_object": "{}/tags/attachTagToObject/{}/{}",
    "remove_tag_from_object": "{}/tags/removeTagFromObject/{}/{}",
    "delete_object": "{}/attributes/delete/{}",
    "tags": "{}/tags",
    "add_attribute": "{}/attributes/add/{}",
    "download_sample": "{}/attributes/downloadSample/",
    "search_events": "{}/events/restSearch/download/",
}

ADD_ACTION = 1
REMOVE_ACTION = 2


class MISPManager:
    """
    MISP Manager
    """

    def __init__(
        self,
        server_address,
        api_key,
        use_ssl=False,
        ca_certificate_file=None,
        logger=None,
    ):
        self.server_address = (
            server_address[:-1] if server_address.endswith("/") else server_address
        )
        self.session = SiemplifySession()
        self.use_ssl = use_ssl
        self.session.verify = self._verify_certificate(ca_certificate_file)
        self.session.headers = HEADERS
        self.session.headers.update({"Authorization": api_key})
        self.parser = MISPParser()
        MISPManager.logger = logger
        self.test_connectivity()

    def _verify_certificate(self, ca_certificate=None):
        if ca_certificate is not None and self.use_ssl:
            return self._save_certificate_file(ca_certificate)

        return self.use_ssl

    def _save_certificate_file(self, ca_certificate_file):
        try:
            file_content = base64.b64decode(ca_certificate_file).decode()
            with open(CA_CERTIFICATE_FILE_PATH, "w") as f:
                f.write(file_content)
                f.close()
            return CA_CERTIFICATE_FILE_PATH
        except Exception as e:
            raise MISPCertificateError(f"Certificate Error: {e}")

    def search_attributes(self, payload, limit=None):
        """
        Search attribute using payload
        :param payload: {str} The request payload.
        :param limit: {str} Get limited attributes.
        :return: {list}
        """
        url = API_ENDPOINTS["search_attributes"].format(self.server_address)

        payload["returnFormat"] = "json"

        response = self.session.post(url, json=payload)

        self.validate_response(response)

        return self.parser.build_siemplify_attribute_objs_from_list_of_json(
            response.json(), limit
        )

    def get_attributes(
        self,
        attribute_names=None,
        attribute_uuids=None,
        categories=None,
        types=None,
        attribute_search=None,
        event_id=None,
    ):
        """
        Get Attributes
        :param attribute_names: {list} The attribute names.
        :param categories: {list} The attribute category that belong to.
        :param types: {list} The types of the attributes.
        :param attribute_uuids: {list} The types of the attributes.
        :param attribute_search: {str} The types of the attribute search.
        :param event_id: {str} The unique identifier specifying the event.
        :return: {str}
        """
        payload = {}
        if attribute_uuids:
            payload.update({"uuid": attribute_uuids})
        elif attribute_names:
            payload.update({"value": attribute_names})
        if categories:
            payload.update({"category": categories})
        if types:
            payload.update({"type": types})
        if (
            attribute_search
            and attribute_search == ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT]
            and event_id
        ):
            payload.update({"eventid": event_id})

        return self.search_attributes(payload)

    def get_attributes_from_object(
        self, event_id, object_uuid, attribute_names, attribute_uuids, categories, types
    ):
        """
        Get the UUID of an attribute from a specific object
        :param event_id: {str} The unique identifier specifying the event.
        :param object_uuid: {str} The uuid of the object that contains the attribute
        :param attribute_names: {list} The names of the attributes.
        :param attribute_uuids: {list} The uuids of the attributes.
        :param categories: {list} The categories which the attribute belongs to.
        :param types: {list} The types of the attribute.
        :return: [{Attribute}] The Attribute instance in list
        """
        event = self.get_event_by_id(event_id)

        objects = [
            self.parser.build_siemplify_misp_obj(misp_object)
            for misp_object in event.raw_data.get("Object", [])
        ]

        object_found = False
        found_attributes = []
        for misp_obj in objects:
            if misp_obj.uuid == object_uuid:
                object_found = True

                for attribute in misp_obj.attributes:
                    if attribute.category in categories and attribute.type in types:
                        if (
                            attribute_uuids and (attribute.uuid in attribute_uuids)
                        ) or attribute.value in attribute_names:
                            found_attributes.append(attribute)

        if found_attributes:
            return found_attributes

        if not object_found:
            raise MISPManagerObjectNotFoundError(
                f"Unable to find object {object_uuid} in event {event_id}"
            )

        raise MISPManagerAttributeNotFoundError(
            f"Matching attribute was not found in given object {object_uuid} in event {event_id}"
        )

    def get_attribute_id(self, event_id, attribute_name, category, attribute_type):
        """
        Get Attribute ID
        :param event_id: {str} The unique identifier specifying the event.
        :param attribute_name: {str} The name of the attribute.
        :param category: {str} The category which the attribute belongs to.
        :param attribute_type: {str} The type of the attribute.
        :return: {str}
        """
        payload = {
            "eventid": event_id,
            "value": attribute_name,
            "category": category,
            "Type": attribute_type,
        }

        attributes = self.search_attributes(payload)

        if not attributes:
            raise MISPManagerError(
                "Attribute not found for given parameters.(event id:{}, attribute name:{}, "
                "category:{}, Type:{})".format(
                    event_id, attribute_name, category, attribute_type
                )
            )

        return attributes[0].id

    def get_all_tags(self):
        """
        Get all tags from system
        :return: {list} List of tags
        """
        url = API_ENDPOINTS["tags"].format(self.server_address)

        response = self.session.post(url)

        self.validate_response(response)

        return self.parser.build_list_of_siemplify_tag_objs(response.json())

    def find_tags_with_names(self, names):
        """
        Map tags name and id
        :param names: {list} Tag names to create the map
        :return: {dict}, {list} Dict for tags name and id, list of not existing tag names
        """
        all_tags = self.get_all_tags()
        existing_tags = list(filter(lambda tag: tag.name in names, all_tags))
        tags_with_name = {tag.name: tag for tag in existing_tags}
        return tags_with_name, [name for name in names if not tags_with_name.get(name)]

    def get_tag_id_by(self, criteria, value):
        """
        Get tag ID by criteria
        :param criteria: {str} The field name to filter tag
        :param value: {str} The exact value of criteria to filter tag.
        :return: {str} Tag ID
        """
        all_tags = self.get_all_tags()
        tag_result = list(filter(lambda tag: getattr(tag, criteria) == value, all_tags))
        if tag_result:
            return tag_result[0].id

    def find_tag_id_or_fail(self, tag_name):
        """
        Get tag ID by name or fail
        :param tag_name: {str} The tag name
        :return: {str} Tag ID
        """
        tag_id = self.get_tag_id_by("name", tag_name)
        if tag_id is None:
            raise MISPManagerTagNotFoundError(f"There is no tag with name '{tag_name}'")

        return tag_id

    def get_event_objects(self, event_id, limit=None):
        """
        Get event objects
        :param event_id: {str} The ID of the event
        :param limit: {int} Max number of results to return
        :return: {[Object]} List of found objects
        """
        return self.parser.build_siemplify_misp_objects_from_events(
            self.get_event_by_id(event_id)
        )[:limit]

    def add_remove_tag_to_attribute(self, action, tag_name, uuid):
        """
        Add/Remove Tag to an Attribute
        :param action: {int} The action name. The possible values are ADD_ACTION and REMOVE_ACTION constants
        :param tag_name: {list} The names of the tags.
        :param uuid: {str} The uuid of attribute.
        :return: {ApiMessage}
        """
        action_endpoint_map = {
            ADD_ACTION: "attach_tag_to_object",
            REMOVE_ACTION: "remove_tag_from_object",
        }

        endpoint = action_endpoint_map[action]

        url = API_ENDPOINTS[endpoint].format(
            self.server_address, uuid, self.find_tag_id_or_fail(tag_name)
        )

        response = self.session.post(url)

        self.validate_response(response)

        return self.parser.build_siemplify_api_message_obj(response.json())

    def add_sighting_to_attribute(
        self, attribute_uuid, date, time, sighting_type, source=None
    ):
        """
        Add a sighting to an Attribute
        :param attribute_uuid: {str} Attribute uuid
        :param date: {str} The date of the sighting
        :param time: {str} The time of the sighting
        :param sighting_type: {str} The type of the attribute (0/1/2)
        :param source: {str} The source of the sighting
        :return: {ApiSighting} The added sighting
        """
        url = API_ENDPOINTS["add_sighting"].format(self.server_address)

        payload = {
            "uuid": attribute_uuid,
            "type": sighting_type,
            "source": source,
            "date": date,
            "time": time,
        }

        payload = {k: v for k, v in payload.items() if v}
        response = self.session.post(url, json=payload)

        self.validate_response(response)
        return self.parser.build_siemplify_api_sighting_obj(response.json())

    def get_sighting_type(self, sighting_text):
        """
        Get sighting type (numeric) from textual sighting value
        :param sighting_text: {str} The sighting textual value
        :return: {str} THe numeric type of the sighting
        """
        for key, value in SIGHTING_LEVELS.items():
            if sighting_text == value:
                return key

        raise MISPManagerError(f"Sighting type {sighting_text} is invalid")

    def list_attribute_sightings(self, attribute_id):
        """
        List the sightings of Attribute
        :param attribute_id: {str} The id of the attribute
        :return: {[ApiSighting]} List of sightings of an attribute
        """
        url = API_ENDPOINTS["list_sighting"].format(self.server_address, attribute_id)
        response = self.session.get(url)

        self.validate_response(response)

        return [
            self.parser.build_siemplify_api_sighting_obj(sighting)
            for sighting in response.json()
        ]

    def delete_attribute(self, uuid):
        """
        Delete an Attribute bu uuid
        :param uuid: {str} The uuid of the attribute
        :return: {ApiMessage}
        """
        url = API_ENDPOINTS["delete_object"].format(self.server_address, uuid)

        response = self.session.post(url)

        self.validate_response(response)

        return self.parser.build_siemplify_api_message_obj(response.json())

    def delete_event(self, event_id):
        """
        Delete Event
        :param event_id: {str} The unique identifier specifying the event.
        :return: {ApiMessage}
        """
        url = API_ENDPOINTS["delete_event"].format(self.server_address, event_id)

        response = self.session.post(url)

        self.validate_response(response)

        return self.parser.build_siemplify_api_message_obj(response.json())

    def unpublish_event(self, event_id):
        """
        UnPublish Event
        :param event_id: {str} The unique event id or uuid.
        :return: {Event}
        """

        url = API_ENDPOINTS["unpublish_event"].format(self.server_address, event_id)

        response = self.session.post(url, json={})

        self.validate_response(response)

        return self.parser.build_siemplify_event_obj(response.json())

    def publish_event(self, event_id):
        """
        Publish Event
        :param event_id: {str} The unique event id or uuid.
        :return: {Event}
        """

        url = API_ENDPOINTS["publish_event"].format(self.server_address, event_id)

        response = self.session.post(url, json={})

        self.validate_response(response)

        return self.parser.build_siemplify_event_obj(response.json())

    def add_or_remove_tag(self, action, event_id, tag_id):
        """
        Add or remove Tag to an Event
        :param action: {int} The action name. The possible values are ADD_ACTION and REMOVE_ACTION constants
        :param event_id: {str} The unique identifier specifying the event to add/remove tag to.
        :param tag_id: {str} The id of the tag to add/remove to an event.
        :return: {SaveResponse}
        """
        action_endpoint_map = {ADD_ACTION: "add_tag", REMOVE_ACTION: "remove_tag"}

        endpoint = action_endpoint_map[action]

        url = API_ENDPOINTS[endpoint].format(self.server_address)

        payload = {"request": {"Event": {"id": event_id, "tag": tag_id}}}

        response = self.session.post(url, json=payload)

        self.validate_response(response)

        return self.parser.build_siemplify_save_response_obj(response.json())

    def test_connectivity(self):
        """
        Test connectivity to MISP
        :return: {bool} True if successful, exception otherwise.
        """
        self.get_events(limit=1, last="1m")
        return True

    def get_events(
        self,
        type=None,
        value=None,
        category=None,
        organization=None,
        tags=None,
        since=None,
        to=None,
        last=None,
        event_id=None,
        uuid=None,
        limit=None,
    ):
        """
        Search for events
        :param type: {str} Type of an even'ts attribute to search for
        :param value: {str} Value in the event to search for
        :param category: {str} Category of the
        :param organization: {str} The organization of the event
        :param tags: {str} To include a tag in the results just write its names into this
            parameter. To exclude a tag prepend it with a '!'. You can also chain several
            tag commands together with the '&&' operator. Please be aware the colons (:)
            cannot be used in the tag search. Use semicolons instead (the search will
            automatically search for colons instead).
        :param since: {str} Events with the date set to a date after the one specified in
            the from field (format: 2015-02-15). This filter will use the date of the
            event.
        :param to: {str} Events with the date set to a date before the one specified in
        the to field (format: 2015-02-15). This filter will use the date of the event.
        :param last: {str} Events published within the last x amount of time, where x can
            be defined in days, hours, minutes (for example 5d or 12h or 30m). This filter
            will use the published timestamp of the event.
        :param event_id: {int} The events that should be included / excluded from the search.
            (Exclude with !)
        :param uuid: {str} The returned events must include an attribute with the given UUID,
            or alternatively the event's UUID must match the value(s) passed.
        :param limit: {int} Max num of events to return
        :return: {list} The matching events
        """
        url = API_ENDPOINTS["search_events"].format(self.server_address)
        payload = {
            "type": type,
            "value": value,
            "category": category,
            "org": organization,
            "tags": tags,
            "from": since,
            "to": to,
            "last": last,
            "eventid": event_id,
            "uuid": uuid,
            "limit": limit,
        }

        payload = {k: v for k, v in payload.items() if v}

        response = self.session.post(url, json=payload)
        self.validate_response(response, "Unable to get events")

        return self.parser.build_siemplify_event_objs_from_list_of_json(response.json())

    def get_event_by_id_or_raise(self, event_id):
        try:
            return self.get_event_by_id(event_id)
        except:
            raise MISPManagerEventIdNotFoundError

    def get_event_by_id(self, event_id):
        url = f"{self.server_address}/events/{event_id}"
        response = self.session.get(url)
        self.validate_response(response, f"Unable to get event {event_id}")

        return self.parser.build_siemplify_event_obj(response.json())

    def get_object_by_id(self, object_id):
        url = f"{self.server_address}/objects/view/{object_id}"
        response = self.session.get(url)
        self.validate_response(response, f"Unable to get object {object_id}")

        return self.parser.build_siemplify_misp_obj(response.json().get("Object"))

    def get_reputation(self, type, entity, limit=None):
        """
        Get the events that are connected to a given entity
        :param entity: {str} The entity
        :param type: {str} The type of the entity to search for. Valid values:
            ip-src, domain, hostname, text, url, ip-dst, port, filename, md5,
            sha256, etc.
        :param limit: {int} Max num of events to return
        :return: {list} List of relevant events
        """
        return self.get_events(type, entity, limit=limit)

    def upload_file(
        self,
        file_path,
        event_id=None,
        distribution=1,
        to_ids=False,
        category=None,
        comment=None,
    ):
        """
        Upload file sample to MISP
        :param file_path: {str} The path of the file to upload
        :param event_id: {int} The Event's ID is optional. Not supplying
            an event ID will cause MISP to create a single new event for all
            of the POSTed malware samples. You can define the default settings
            for the event, otherwise a set of default settings will be used.
        :param distribution: {int} The distribution setting used for the
            attributes and for the newly created event, if relevant. [0-3]
        :param to_ids: {bool} You can flag all attributes created during
            the transaction to be marked as "to_ids" or not.
        :param category: {str} The category that will be assigned to the
            uploaded samples. Valid options are:
                - Payload delivery
                - Artifacts dropped
                - Payload Installation
                - External Analysis.
        :param comment: {str} This will populate the comment field of any
            attribute created using this API.
        :return: {bool} True if successful, exception otherwise
        """
        url = f"{self.server_address}/events/upload_sample/{event_id or ''}"

        if not os.path.exists(file_path):
            raise MISPManagerError(f"File {file_path} doesn't exist")

        file_name = os.path.basename(file_path)
        file_content = open(file_path, "rb").read()

        file_data = {
            "filename": file_name,
            "data": base64.b64encode(file_content).decode(),
        }

        payload = {
            "request": {
                "files": [file_data],
                "event_id": event_id,
                "distribution": distribution,
                "to_ids": to_ids,
                "category": category,
                "comment": comment,
            }
        }

        payload["request"] = {
            k: v for k, v in payload["request"].items() if v is not None
        }

        response = self.session.post(url, json=payload)
        self.validate_response(response, "Unable to upload file")

        return response.json()

    def create_event(
        self,
        event_name,
        distribution=1,
        comment=None,
        published=False,
        threat_level=1,
        analysis=0,
    ):
        """
        Create a new MISP event
        :param event_name: {str} The name of the event
        :param distribution: {int} The distribution setting used for the attributes and for the newly created event, if relevant. [0-3]
        :param comment: {str} This will populate the comment field of any attribute created using this API.
        :param published: {bool} Whether to publish the event or not
        :param threat_level: {int} The threat level ID of the newly created event, if applicable. [1-4]
        :param analysis: {int} The analysis level of the newly created event, if applicable. [0-2]
        :return: {int} The id of the new event
        """
        url = f"{self.server_address}/events/"

        payload = {
            "Event": {
                "date": arrow.now().date().isoformat(),
                "threat_level_id": threat_level,
                "distribution": distribution,
                "info": event_name,
                "analysis": analysis,
                "published": published,
                "comment": comment,
            }
        }

        payload["Event"] = {k: v for k, v in payload["Event"].items() if v is not None}

        try:
            response = self.session.post(url, json=payload)
            self.validate_response(response, "Unable to create event")
            return self.parser.build_siemplify_event_obj(response.json())
        except Exception as e:
            if "Could not add Event" in str(e):
                raise MISPManagerCreateEventError()
            raise

    def add_attribute(
        self,
        event_id,
        value,
        type="text",
        category="",
        to_ids=False,
        distribution=1,
        comment=None,
    ):
        """
        Add an attribute to an event
        :param event_id: {int} The event id to add the attribute to
        :param type: {str} The type of the attribute. Available values:
            ip-src, ip-dst, md5, sha256, sha1, filename, hostname, domain,
            url and etc.
        :param value: {str} The value to add
        :param category: {Str} The category of the attribute. Available values:
            Targeting data, Payload delivery, Artifacts dropped, Network activity, Attribution,
            External analysis and etc.
        :param to_ids: {bool} Whether to flag the attribute as "to_ids" or
            not. Default: False
        :param distribution: {int} The distribution setting for the
            attribute. [0-3]
        :param comment: {str} This will populate the comment field of the
            attribute created using this API.
        :return: {int} The id of the created attribute
        """
        url = API_ENDPOINTS["add_attribute"].format(self.server_address, event_id)

        payload = {
            "Attribute": {
                "distribution": distribution,
                "to_ids": to_ids,
                "category": category,
                "comment": comment,
                "type": type,
                "value": value,
            }
        }

        payload["Attribute"] = {
            k: v for k, v in payload["Attribute"].items() if v is not None
        }

        response = self.session.post(url, json=payload)
        self.validate_response(response, "Unable to add attribute")

        return self.parser.build_siemplify_attribute_obj(response.json())

    def set_unset_ids_flag_for_attribute(self, attribute_id, to_ids=True):
        """
        Set or unset IDS flag on an attribute
        :param attribute_id: {str}
        :param to_ids: {bool} Whether to flag the attribute as "to_ids" or not. By default, set to True
        :return: {bool} True if successful, exception otherwise
        """
        url = API_ENDPOINTS["edit_attribute"].format(self.server_address, attribute_id)

        response = self.session.post(url, json={"to_ids": 1 if to_ids else 0})

        self.validate_response(response)

        return True

    def add_file_object(
        self, event_id, filename=None, md5=None, sha1=None, sha256=None, ssdeep=None
    ):
        """
        Add a MISP file object to a given event
        :param event_id: {int} The ID of the event
        :param filename: {str} The filename of the file
        :param md5: {str} The MD5 of the file
        :param sha1: {str} The SHA1 of the file
        :param sha256: {str} The SHA256 of the file
        :param ssdeep: {str} The ssdeep of the file
        :return: {MISPObject} the created object
        """
        url = API_ENDPOINTS["add_object"].format(
            self.server_address, event_id, self.get_template_object_id_by_name("file")
        )
        payload = {"Object": {"distribution": "5", "comment": ""}, "Attribute": {}}

        if filename:
            payload["Attribute"]["2"] = {
                "object_relation": "filename",
                "type": "filename",
                "category": "Payload delivery",
                "value": filename,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if md5:
            payload["Attribute"]["0"] = {
                "object_relation": "md5",
                "type": "md5",
                "category": "Payload delivery",
                "value": md5,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if sha1:
            payload["Attribute"]["6"] = {
                "object_relation": "sha1",
                "type": "sha1",
                "category": "Payload delivery",
                "value": sha1,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if sha256:
            payload["Attribute"]["9"] = {
                "object_relation": "sha256",
                "type": "sha256",
                "category": "Payload delivery",
                "value": sha256,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if ssdeep:
            payload["Attribute"]["10"] = {
                "object_relation": "ssdeep",
                "type": "ssdeep",
                "category": "Payload delivery",
                "value": ssdeep,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        response = self.session.post(url, json=payload)
        self.validate_response(
            response, f"Unable to create file object for event {event_id}"
        )

        return self.parser.build_siemplify_misp_obj(response.json().get("Object"))

    def add_ip_port_object(
        self,
        event_id,
        dst_port=None,
        src_port=None,
        domain=None,
        hostname=None,
        src_ip=None,
        dst_ip=None,
    ):
        """
        Add an IP Port object to a given event
        :param event_id: {int} The ID of the event
        :param dst_port: {int} The destination port
        :param src_port: {int} The source port
        :param domain: {str} The domain
        :param hostname: {str} The hostname
        :param src_ip: {str} The source  IP
        :param dst_ip: {str} The setination IP
        :return: {MISPObject} The created objevt
        """
        url = API_ENDPOINTS["add_object"].format(
            self.server_address,
            event_id,
            self.get_template_object_id_by_name("ip-port"),
        )
        payload = {"Object": {"distribution": "5", "comment": ""}, "Attribute": {}}

        if dst_port:
            payload["Attribute"]["0"] = {
                "object_relation": "dst-port",
                "type": "port",
                "category": "Network activity",
                "value": dst_port,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if src_port:
            payload["Attribute"]["1"] = {
                "object_relation": "src-port",
                "type": "port",
                "category": "Network activity",
                "value": src_port,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if domain:
            payload["Attribute"]["2"] = {
                "object_relation": "domain",
                "type": "domain",
                "category": "Network activity",
                "value": domain,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if hostname:
            payload["Attribute"]["3"] = {
                "object_relation": "hostname",
                "type": "hostname",
                "category": "Network activity",
                "value": hostname,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if src_ip:
            payload["Attribute"]["4"] = {
                "object_relation": "ip-src",
                "type": "ip-src",
                "category": "Network activity",
                "value": src_ip,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if dst_ip:
            payload["Attribute"]["5"] = {
                "object_relation": "ip-dst",
                "type": "ip-dst",
                "category": "Network activity",
                "value": dst_ip,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        response = self.session.post(url, json=payload)
        self.validate_response(
            response, f"Unable to create IP Port object for event {event_id}"
        )
        return self.parser.build_siemplify_misp_obj(response.json().get("Object"))

    def add_network_connection_object(
        self,
        event_id,
        dst_port=None,
        src_port=None,
        src_hostname=None,
        dst_hostname=None,
        src_ip=None,
        dst_ip=None,
        l3_protocol=None,
        l4_protocol=None,
        l7_protocol=None,
    ):
        """
        Create an Network Connection object for a given event
        :param event_id: {int} The ID of the event
        :param dst_port: {int} The destination port
        :param src_port: {int} The source port
        :param src_hostname: {str} The source hostname
        :param dst_hostname: {str} The destination hostname
        :param src_ip: {str} The source IP
        :param dst_ip: {str} The destination IP
        :param l3_protocol: {str} The L3 protocol of the connection
        :param l4_protocol: {str} The L4 protocol of the connection
        :param l7_protocol: {str} The L7 protocol of the connection
        :return: {MISPObject} The created object
        """
        url = API_ENDPOINTS["add_object"].format(
            self.server_address,
            event_id,
            self.get_template_object_id_by_name("network-connection"),
        )
        payload = {"Object": {"distribution": "5", "comment": ""}, "Attribute": {}}

        if dst_port:
            payload["Attribute"]["3"] = {
                "object_relation": "dst-port",
                "type": "port",
                "category": "Network activity",
                "value": dst_port,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if src_port:
            payload["Attribute"]["2"] = {
                "object_relation": "src-port",
                "type": "port",
                "category": "Network activity",
                "value": src_port,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if dst_hostname:
            payload["Attribute"]["5"] = {
                "object_relation": "hostname-dst",
                "type": "hostname",
                "category": "Network activity",
                "value": dst_hostname,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if src_hostname:
            payload["Attribute"]["4"] = {
                "object_relation": "hostname-src",
                "type": "hostname",
                "category": "Network activity",
                "value": src_hostname,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if dst_ip:
            payload["Attribute"]["1"] = {
                "object_relation": "ip-dst",
                "type": "ip-dst",
                "category": "Network activity",
                "value": dst_ip,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if src_ip:
            payload["Attribute"]["0"] = {
                "object_relation": "ip-src",
                "type": "ip-src",
                "category": "Network activity",
                "value": src_ip,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if l3_protocol:
            payload["Attribute"]["8"] = {
                "object_relation": "layer3-protocol",
                "type": "text",
                "category": "Other",
                "value": l3_protocol,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if l4_protocol:
            payload["Attribute"]["9"] = {
                "object_relation": "layer4-protocol",
                "type": "text",
                "category": "Other",
                "value": l4_protocol,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if l7_protocol:
            payload["Attribute"]["10"] = {
                "object_relation": "layer7-protocol",
                "type": "text",
                "category": "Other",
                "value": l7_protocol,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        response = self.session.post(url, json=payload)
        self.validate_response(
            response, f"Unable to create Network Connection object for event {event_id}"
        )
        return self.parser.build_siemplify_misp_obj(response.json().get("Object"))

    def add_url_object(
        self,
        event_id,
        url=None,
        port=None,
        first_seen=None,
        last_seen=None,
        domain=None,
        text=None,
        ip=None,
        host=None,
    ):
        """
        Add URL object to a given event
        :param event_id: {int} The ID of the event
        :param url: {str} The URL
        :param port: {int} The port
        :param first_seen: {str} The first seen timestamp of the url (YYYY-mm-DD HH:MM:SS)
        :param last_seen: {str} The last seen timestamp of the url (YYYY-mm-DD HH:MM:SS)
        :param domain: {str} The domain of the URL
        :param text: {str} Free text
        :param ip: {str} The IP related to the URL
        :param host: {str} The host of the URL
        :return: {MISPObject} The created object
        """
        api_url = API_ENDPOINTS["add_object"].format(
            self.server_address, event_id, self.get_template_object_id_by_name("url")
        )
        payload = {"Object": {"distribution": "5", "comment": ""}, "Attribute": {}}

        if url:
            payload["Attribute"]["0"] = {
                "object_relation": "url",
                "type": "url",
                "category": "Network activity",
                "value": url,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if port:
            payload["Attribute"]["2"] = {
                "object_relation": "port",
                "type": "port",
                "category": "Network activity",
                "value": port,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if first_seen:
            payload["Attribute"]["5"] = {
                "object_relation": "first-seen",
                "type": "datetime",
                "category": "Other",
                "value": first_seen,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if last_seen:
            payload["Attribute"]["6"] = {
                "object_relation": "last-seen",
                "type": "datetime",
                "category": "Other",
                "value": last_seen,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if domain:
            payload["Attribute"]["9"] = {
                "object_relation": "domain",
                "type": "domain",
                "category": "Network activity",
                "value": domain,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if ip:
            payload["Attribute"]["10"] = {
                "object_relation": "ip",
                "type": "ip-dst",
                "category": "Network activity",
                "value": ip,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if host:
            payload["Attribute"]["11"] = {
                "object_relation": "host",
                "type": "hostname",
                "category": "Network activity",
                "value": host,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if text:
            payload["Attribute"]["12"] = {
                "object_relation": "text",
                "type": "text",
                "category": "Other",
                "value": text,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        response = self.session.post(api_url, json=payload)
        self.validate_response(
            response, f"Unable to create URL object for event {event_id}"
        )
        return self.parser.build_siemplify_misp_obj(response.json().get("Object"))

    def add_virus_total_report_object(
        self,
        event_id,
        permalink=None,
        comment=None,
        detection_ratio=None,
        community_score=None,
        first_submission=None,
        last_submission=None,
    ):
        """
        Create a VT report object for a given event
        :param event_id: {int} The ID of the event
        :param permalink: {str} The VT permalink
        :param comment: {str} A comment to that report
        :param detection_ratio: {str} The detection ratio
        :param community_score: {str} The community score of that report
        :param first_submission: {str} The first submission for that report (YYYY-mm-DD HH:MM:SS)
        :param last_submission: {str} The last submission for that report (YYYY-mm-DD HH:MM:SS)
        :return: {MISPObject} The created object
        """
        url = API_ENDPOINTS["add_object"].format(
            self.server_address,
            event_id,
            self.get_template_object_id_by_name("virustotal-report"),
        )
        payload = {"Object": {"distribution": "5", "comment": ""}, "Attribute": {}}

        if permalink:
            payload["Attribute"]["0"] = {
                "object_relation": "permalink",
                "type": "link",
                "category": "External analysis",
                "value": permalink,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if comment:
            payload["Attribute"]["1"] = {
                "object_relation": "comment",
                "type": "text",
                "category": "External analysis",
                "value": comment,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if first_submission:
            payload["Attribute"]["2"] = {
                "object_relation": "first-submission",
                "type": "datetime",
                "category": "Other",
                "value": first_submission,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if last_submission:
            payload["Attribute"]["3"] = {
                "object_relation": "last-submission",
                "type": "datetime",
                "category": "Other",
                "value": last_submission,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if detection_ratio:
            payload["Attribute"]["4"] = {
                "object_relation": "detection-ratio",
                "type": "text",
                "category": "External analysis",
                "value": detection_ratio,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        if community_score:
            payload["Attribute"]["5"] = {
                "object_relation": "community-score",
                "type": "text",
                "category": "External analysis",
                "value": community_score,
                "to_ids": "0",
                "disable_correlation": "0",
                "distribution": "5",
                "comment": "",
            }

        response = self.session.post(url, json=payload)
        self.validate_response(response)
        return self.parser.build_siemplify_misp_obj(response.json().get("Object"))

    def download_sample(self, event_id=None):
        """
        Download a sample from MISP
        :param event_id: {int} If set, it will only fetch data from the given event ID.
        :return: {str} The content of the sample
        """
        url = API_ENDPOINTS["download_sample"].format(self.server_address)
        payload = {"request": {"allSamples": 1, "eventID": event_id}}

        response = self.session.post(url, json=payload)
        self.validate_response(response, "Unable to download file")

        return self.parser.build_list_of_misp_attachments(response.json())

    def get_object_templates(self):
        """
        List all the object templates in the MISP
        :return: {[ObjectTemplate]} List of found object templates
        """
        url = f"{self.server_address}/objectTemplates/"
        response = self.session.get(url)
        self.validate_response(response, "Unable to download file")

        return [
            self.parser.build_siemplify_object_template_obj(template_obj)
            for template_obj in response.json()
        ]

    def get_template_object_id_by_name(self, name):
        """
        Get the ID of a template object by its name
        :param name: {str} The name of the object
        :return: {int} The ID of the found template
        """
        template_objects = self.get_object_templates()

        for template_object in template_objects:
            if template_object.name == name:
                return template_object.id

        raise MISPManagerError(f"Object template {name} was not found.")

    @classmethod
    def get_api_error_message(cls, exception):
        """
        Get API error message
        :param exception: {Exception} The api error
        :return: {str} error message
        """
        try:
            return exception.response.json().get("message")
        except:
            return None

    @classmethod
    def validate_response(cls, response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            error_message = cls.get_api_error_message(error)
            if error_message:
                raise MISPManagerError(error_message)
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise MISPManagerError(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise MISPManagerError(
                f"{error_msg}: {response.json().get('message', '')} {response.json().get('errors', '')}"
            )

        return True
