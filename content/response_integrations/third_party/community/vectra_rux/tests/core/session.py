from __future__ import annotations

import re

import requests

from tests.core.product import VectraProduct, mock

API_NAME_TO_PATH = {
    "PING": re.compile(r"/oauth2/token/?$"),
    "LIST_ASSIGNMENTS": re.compile(r"/api/v3\.5/assignments/?$"),
    "ASSIGN_ENTITY": re.compile(r"/api/v3\.5/assignments/?$"),
    "ASSIGNMENT": re.compile(r"/api/v3\.5/assignments/(?P<assignment_id>[^/]+)/?$"),
    "UPDATE_ASSIGNMENT": re.compile(r"/api/v3\.5/assignments/(?P<assignment_id>[^/]+)/?$"),
    "LIST_DETECTIONS": re.compile(r"/api/v3\.5/detections/?$"),
    "LIST_ENTITY_DETECTIONS": re.compile(r"/api/v3\.5/detections/?$"),
    "DESCRIBE_DETECTION": re.compile(r"/api/v3\.5/detections/?$"),
    "SET_DETECTION_STATUS": re.compile(r"/api/v3\.5/detections/?$"),
    "SET_DETECTION_TICKET": re.compile(r"/api/v3\.5/detections/?$"),
    "CLOSE_DETECTIONS": re.compile(r"/api/v3\.5/detections/close/?$"),
    "OPEN_DETECTIONS": re.compile(r"/api/v3\.5/detections/open/?$"),
    "LIST_ENTITIES": re.compile(r"/api/v3\.5/entities/?$"),
    "DESCRIBE_ENTITY": re.compile(r"/api/v3\.5/entities/?$"),
    "SET_ENTITY_UNRESOLVED_PRIORITY": re.compile(r"/api/v3\.5/entities/(?P<entity_id>[^/]+)/?$"),
    "SET_ENTITY_TICKET": re.compile(r"/api/v3\.5/entities/(?P<entity_id>[^/]+)/?$"),
    "TAGGING": re.compile(r"/api/v3\.5/tagging/entity/(?P<entity_id>[^/]+)/?$"),
    "LIST_TAGS": re.compile(r"/api/v3\.5/tagging/entity/(?P<entity_id>[^/]+)/?$"),
    "LIST_ENTITY": re.compile(r"/api/v3\.5/(?P<entity_type>hosts|accounts)/(?P<entity_id>[^/]+)/?$"),
    "LIST_USERS": re.compile(r"/api/v3\.5/users/?$"),
    "LIST_GROUPS": re.compile(r"/api/v3\.5/groups/?$"),
    "UPDATE_GROUP_MEMBERS": re.compile(r"/api/v3\.5/groups/(?P<group_id>[^/]+)/?$"),
    "ADD_NOTE": re.compile(r"/api/v3\.5/entities/(?P<entity_id>[^/]+)/notes/?$"),
    "LIST_ENTITY_NOTES": re.compile(r"/api/v3\.5/entities/(?P<entity_id>[^/]+)/notes/?$"),
    "REMOVE_NOTE": re.compile(r"/api/v3\.5/entities/(?P<entity_id>[^/]+)/notes/(?P<note_id>[^/]+)/?$"),
    "UPDATE_ENTITY_NOTE": re.compile(r"/api/v3\.5/entities/(?P<entity_id>[^/]+)/notes/(?P<note_id>[^/]+)/?$"),
    "DOWNLOAD_PCAP": re.compile(r"/api/v3\.5/detections/(?P<detection_id>[^/]+)/pcap/?$"),
    "QUERY_INVESTIGATION": re.compile(r"/api/v3\.5/investigations/?$"),
    "GET_INVESTIGATION_RESULTS": re.compile(r"/api/v3\.5/investigations/(?P<request_id>[^/]+)/?$"),
    "LIST_DETECTION_EVENTS": re.compile(r"/api/v3\.5/events/detections/?$"),
}


class MockResponse(requests.Response):
    """A requests.Response populated directly from in-memory data, with no
    actual network I/O involved.
    """

    def __init__(self, json_data=None, status_code=200, content=None, headers=None):
        super().__init__()
        self.status_code = status_code
        self.headers.update(headers or {"Content-Type": "application/json"})
        if content is not None:
            self._content = content
        else:
            self._content = requests.compat.json.dumps(json_data or {}).encode("utf-8")
        self._content_consumed = True

    def json(self, **kwargs):
        return requests.compat.json.loads(self._content.decode("utf-8"))


class MockVectraSession(requests.Session):
    """A requests.Session replacement that never touches the network.

    Every `request()` call is routed, by (HTTP method, URL path), to a
    handler that returns a response built from the `VectraProduct`
    instance's current state. Mirrors the shape of VectraRUXManager's
    real API surface without depending on any external mocking library.
    """

    def __init__(self, product: VectraProduct):
        super().__init__()
        self._product = product
        self.request_history = []

    def request(self, method, url, params=None, data=None, json=None, timeout=None, **kwargs):
        self.request_history.append(
            {"method": method, "url": url, "params": params, "data": data, "json": json},
        )

        path = url.split("://", 1)[-1]
        path = "/" + path.split("/", 1)[-1] if "/" in path else path

        for api_name, pattern in API_NAME_TO_PATH.items():
            match = pattern.search(path)
            if match:
                handler = getattr(self, f"_handle_{api_name.lower()}", None)
                if handler:
                    return handler(method, path, params or {}, data, json, match)

        return MockResponse(json_data={"detail": "route not mocked"}, status_code=404)

    # -- individual endpoint handlers ---------------------------------
    def _handle_ping(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.token_status_code
        if status != 200:
            return MockResponse(json_data=p.body_for("PING", {"error": "invalid_client"}), status_code=status)
        return MockResponse(json_data=p.token_response or mock("ping_token"), status_code=200)

    def _handle_list_entities(self, method, path, params, data, json_body, match):
        # DESCRIBE_ENTITY and LIST_ENTITIES both hit `/entities`; DESCRIBE_ENTITY
        # additionally sends an `id` query param, LIST_ENTITIES never does.
        if params.get("id") is not None:
            return self._handle_describe_entity(method, path, params, data, json_body, match)

        p = self._product
        status = p.status_for("LIST_ENTITIES")
        if status != 200:
            return MockResponse(json_data=p.body_for("LIST_ENTITIES", mock("error_bad_request")), status_code=status)
        results = p.list_entities_response if p.list_entities_response is not None else mock("list_entities")
        return MockResponse(json_data={"results": results, "next": None, "count": len(results)}, status_code=200)

    def _handle_describe_entity(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("DESCRIBE_ENTITY")
        if status != 200:
            return MockResponse(json_data=p.body_for("DESCRIBE_ENTITY", mock("error_not_found")), status_code=status)
        results = p.describe_entity_response if p.describe_entity_response is not None else [mock("describe_entity")]
        return MockResponse(json_data={"results": results, "next": None, "count": len(results)}, status_code=200)

    def _handle_describe_detection(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("DESCRIBE_DETECTION")
        if status != 200:
            return MockResponse(json_data=p.body_for("DESCRIBE_DETECTION", mock("error_not_found")), status_code=status)
        results = p.describe_detection_response if p.describe_detection_response is not None else [mock("describe_detection")]
        return MockResponse(json_data={"results": results, "next": None, "count": len(results)}, status_code=200)

    def _handle_list_detections(self, method, path, params, data, json_body, match):
        p = self._product
        if method == "PATCH":
            if json_body and "external_reference_id" in json_body:
                return self._handle_set_detection_ticket(method, path, params, data, json_body, match)
            return self._handle_set_detection_status(method, path, params, data, json_body, match)

        # DESCRIBE_DETECTION and LIST_ENTITY_DETECTIONS both send an `id` param
        # (single id vs. comma-joined ids); LIST_DETECTIONS never sends `id`.
        if params.get("id") is not None:
            if "," in str(params.get("id")):
                return self._handle_list_entity_detections_impl(method, path, params, data, json_body, match)
            return self._handle_describe_detection(method, path, params, data, json_body, match)

        status = p.status_for("LIST_DETECTIONS")
        if status != 200:
            return MockResponse(json_data=p.body_for("LIST_DETECTIONS", mock("error_bad_request")), status_code=status)
        results = p.list_detections_response if p.list_detections_response is not None else mock("list_detections")
        return MockResponse(json_data={"results": results, "next": None, "count": len(results)}, status_code=200)

    def _handle_list_entity_detections_impl(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("LIST_ENTITY_DETECTIONS")
        if status != 200:
            return MockResponse(json_data=p.body_for("LIST_ENTITY_DETECTIONS", mock("error_bad_request")), status_code=status)
        results = p.list_detections_response if p.list_detections_response is not None else mock("list_detections")
        return MockResponse(json_data={"results": results, "next": None, "count": len(results)}, status_code=200)

    def _handle_set_detection_status(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("SET_DETECTION_STATUS")
        if status != 200:
            return MockResponse(json_data=p.body_for("SET_DETECTION_STATUS", mock("error_bad_request")), status_code=status)
        return MockResponse(json_data=p.set_detection_status_response or mock("set_detection_status"), status_code=200)

    def _handle_set_detection_ticket(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("SET_DETECTION_TICKET")
        if status != 200:
            return MockResponse(json_data=p.body_for("SET_DETECTION_TICKET", mock("error_bad_request")), status_code=status)
        return MockResponse(json_data=p.set_detection_ticket_response or mock("set_detection_ticket"), status_code=200)

    def _handle_close_detections(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("CLOSE_DETECTIONS")
        if status != 200:
            return MockResponse(json_data=p.body_for("CLOSE_DETECTIONS", mock("error_bad_request")), status_code=status)
        return MockResponse(json_data=p.close_detections_response or mock("close_detections"), status_code=200)

    def _handle_open_detections(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("OPEN_DETECTIONS")
        if status != 200:
            return MockResponse(json_data=p.body_for("OPEN_DETECTIONS", mock("error_bad_request")), status_code=status)
        return MockResponse(json_data=p.open_detections_response or mock("open_detections"), status_code=200)

    def _handle_set_entity_unresolved_priority(self, method, path, params, data, json_body, match):
        # SET_ENTITY_UNRESOLVED_PRIORITY and SET_ENTITY_TICKET both PATCH
        # `/entities/{id}`; disambiguate by JSON body key.
        if json_body and "external_reference_id" in json_body:
            return self._handle_set_entity_ticket(method, path, params, data, json_body, match)

        p = self._product
        status = p.status_for("SET_ENTITY_UNRESOLVED_PRIORITY")
        if status != 200:
            return MockResponse(json_data=p.body_for("SET_ENTITY_UNRESOLVED_PRIORITY", mock("error_not_found")), status_code=status)
        return MockResponse(json_data=p.set_entity_unresolved_priority_response or mock("set_entity_unresolved_priority"), status_code=200)

    def _handle_set_entity_ticket(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("SET_ENTITY_TICKET")
        if status != 200:
            return MockResponse(json_data=p.body_for("SET_ENTITY_TICKET", mock("error_not_found")), status_code=status)
        return MockResponse(json_data=p.set_entity_ticket_response or mock("set_entity_ticket"), status_code=200)

    def _handle_tagging(self, method, path, params, data, json_body, match):
        p = self._product
        api_name = "LIST_TAGS" if method == "GET" else "TAGGING"
        status = p.status_for(api_name)
        if status != 200:
            return MockResponse(json_data=p.body_for(api_name, mock("error_not_found")), status_code=status)
        if method == "GET":
            return MockResponse(json_data=p.list_tags_response or mock("list_tags"), status_code=200)
        return MockResponse(json_data=p.update_tags_response or mock("update_tags"), status_code=200)

    def _handle_list_tags(self, method, path, params, data, json_body, match):
        return self._handle_tagging(method, path, params, data, json_body, match)

    def _handle_list_entity(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("LIST_ENTITY")
        if status != 200:
            return MockResponse(json_data=p.body_for("LIST_ENTITY", mock("error_not_found")), status_code=status)
        return MockResponse(json_data=p.specific_entity_info_response or mock("specific_entity_info"), status_code=200)

    def _handle_list_users(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("LIST_USERS")
        if status != 200:
            return MockResponse(json_data=p.body_for("LIST_USERS", mock("error_bad_request")), status_code=status)
        results = p.list_users_response if p.list_users_response is not None else mock("list_users")
        return MockResponse(json_data={"results": results, "next": None, "count": len(results)}, status_code=200)

    def _handle_list_groups(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("LIST_GROUPS")
        if status != 200:
            return MockResponse(json_data=p.body_for("LIST_GROUPS", mock("error_bad_request")), status_code=status)
        results = p.list_groups_response if p.list_groups_response is not None else mock("list_groups")
        return MockResponse(json_data={"results": results, "next": None, "count": len(results)}, status_code=200)

    def _handle_update_group_members(self, method, path, params, data, json_body, match):
        p = self._product
        if method == "GET":
            status = p.status_for("UPDATE_GROUP_MEMBERS_GET")
            if status != 200:
                return MockResponse(json_data=p.body_for("UPDATE_GROUP_MEMBERS_GET", mock("error_not_found")), status_code=status)
            return MockResponse(json_data=p.group_members_response or mock("group_members"), status_code=200)

        status = p.status_for("UPDATE_GROUP_MEMBERS")
        if status != 200:
            return MockResponse(json_data=p.body_for("UPDATE_GROUP_MEMBERS", mock("error_not_found")), status_code=status)
        membership_action = (params or {}).get("membership_action")
        default = mock("group_assign_result") if membership_action == "append" else mock("group_remove_result")
        return MockResponse(json_data=p.group_update_response or default, status_code=200)

    def _handle_add_note(self, method, path, params, data, json_body, match):
        p = self._product
        if method == "GET":
            return self._handle_list_entity_notes(method, path, params, data, json_body, match)
        status = p.status_for("ADD_NOTE")
        if status != 200:
            return MockResponse(json_data=p.body_for("ADD_NOTE", mock("error_not_found")), status_code=status)
        return MockResponse(json_data=p.add_note_response or mock("add_note"), status_code=200)

    def _handle_list_entity_notes(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("LIST_ENTITY_NOTES")
        if status != 200:
            return MockResponse(json_data=p.body_for("LIST_ENTITY_NOTES", mock("error_not_found")), status_code=status)
        results = p.list_entity_notes_response if p.list_entity_notes_response is not None else mock("list_entity_notes")
        return MockResponse(json_data=results, status_code=200)

    def _handle_remove_note(self, method, path, params, data, json_body, match):
        p = self._product
        if method == "PATCH":
            return self._handle_update_entity_note(method, path, params, data, json_body, match)
        status = p.status_for("REMOVE_NOTE")
        if status != 200:
            return MockResponse(
                json_data=p.body_for("REMOVE_NOTE", mock("error_not_found")),
                status_code=status,
                headers={"Content-Type": "application/json"},
            )
        return MockResponse(content=b"", status_code=200, headers={"Content-Type": "application/json"})

    def _handle_update_entity_note(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("UPDATE_ENTITY_NOTE")
        if status != 200:
            return MockResponse(json_data=p.body_for("UPDATE_ENTITY_NOTE", mock("error_not_found")), status_code=status)
        return MockResponse(json_data=p.update_note_response or mock("update_note"), status_code=200)

    def _handle_download_pcap(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.download_pcap_status_code
        if status != 200:
            return MockResponse(json_data={"detail": "File Not Found"}, status_code=status)
        return MockResponse(
            content=p.download_pcap_content,
            status_code=200,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Disposition": f"attachment; filename={p.download_pcap_filename}",
            },
        )

    def _handle_list_assignments(self, method, path, params, data, json_body, match):
        if method == "POST":
            return self._handle_assign_entity(method, path, params, data, json_body, match)
        p = self._product
        status = p.status_for("LIST_ASSIGNMENTS")
        if status != 200:
            return MockResponse(json_data=p.body_for("LIST_ASSIGNMENTS", mock("error_bad_request")), status_code=status)
        results = p.list_assignments_response if p.list_assignments_response is not None else mock("list_assignments")
        return MockResponse(json_data={"results": results, "next": None, "count": len(results)}, status_code=200)

    def _handle_assign_entity(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("ASSIGN_ENTITY")
        if status != 200:
            return MockResponse(json_data=p.body_for("ASSIGN_ENTITY", mock("error_bad_request")), status_code=status)
        return MockResponse(json_data=p.assign_entity_response or mock("assign_entity_result"), status_code=200)

    def _handle_assignment(self, method, path, params, data, json_body, match):
        p = self._product

        if method == "DELETE":
            status = p.remove_assignment_status_code
            if status != 200:
                return MockResponse(json_data=mock("error_not_found"), status_code=status)
            return MockResponse(content=p.remove_assignment_body, status_code=200)

        api_name = "UPDATE_ASSIGNMENT" if method == "PUT" else "ASSIGNMENT"
        status = p.status_for(api_name)
        if status != 200:
            return MockResponse(json_data=p.body_for(api_name, mock("error_not_found")), status_code=status)
        if method == "PUT":
            return MockResponse(json_data=p.update_assignment_response or mock("assignment_wrapped"), status_code=200)
        return MockResponse(json_data=p.assignment_response or mock("assignment_wrapped"), status_code=200)

    def _handle_update_assignment(self, method, path, params, data, json_body, match):
        return self._handle_assignment(method, path, params, data, json_body, match)

    def _handle_query_investigation(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("QUERY_INVESTIGATION")
        if status != 200:
            return MockResponse(json_data=p.body_for("QUERY_INVESTIGATION", mock("error_bad_request")), status_code=status)
        return MockResponse(json_data=p.query_investigation_response or mock("query_investigation"), status_code=200)

    def _handle_get_investigation_results(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("GET_INVESTIGATION_RESULTS")
        if status != 200:
            return MockResponse(json_data=p.body_for("GET_INVESTIGATION_RESULTS", mock("error_not_found")), status_code=status)
        results = p.investigation_results_response if p.investigation_results_response is not None else mock("investigation_results")
        return MockResponse(json_data={"data": results, "next": None, "count": len(results)}, status_code=200)

    def _handle_list_entity_detections(self, method, path, params, data, json_body, match):
        return self._handle_list_detections(method, path, params, data, json_body, match)

    def _handle_list_detection_events(self, method, path, params, data, json_body, match):
        p = self._product
        status = p.status_for("LIST_DETECTION_EVENTS")
        if status != 200:
            return MockResponse(json_data=p.body_for("LIST_DETECTION_EVENTS", mock("error_bad_request")), status_code=status)
        return MockResponse(json_data=p.list_detection_events_response or mock("list_detection_events"), status_code=200)
