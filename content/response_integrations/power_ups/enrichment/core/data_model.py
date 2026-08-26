# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from datetime import datetime

import requests
import whois_alt


class ContactInfo:
    def __init__(
        self,
        handle=None,
        name=None,
        organization=None,
        email=None,
        phone=None,
        street=None,
        city=None,
        state=None,
        postalcode=None,
        country=None,
    ):
        self.handle = handle
        self.name = name
        self.organization = organization
        self.email = email
        self.phone = phone
        self.street = street
        self.city = city
        self.state = state
        self.postalcode = postalcode
        self.country = country

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}


class WhoisData:
    def __init__(
        self,
        id=None,
        status=None,
        creation_date=None,
        expiration_date=None,
        updated_date=None,
        registrar=None,
        whois_server=None,
        nameservers=None,
        emails=None,
        contacts=None,
        raw=None,
    ):
        self.id = id
        self.status = status
        self.creation_date = creation_date
        self.expiration_date = expiration_date
        self.updated_date = updated_date
        self.registrar = registrar
        self.whois_server = whois_server
        self.nameservers = nameservers
        self.emails = emails
        self.contacts = contacts or {
            "registrant": None,
            "tech": None,
            "admin": None,
            "billing": None,
        }
        self.raw = raw

    def to_dict(self):
        res = {
            "id": self.id,
            "status": self.status,
            "creation_date": self.creation_date,
            "expiration_date": self.expiration_date,
            "updated_date": self.updated_date,
            "registrar": self.registrar,
            "whois_server": self.whois_server,
            "nameservers": self.nameservers,
            "emails": self.emails,
            "raw": self.raw,
        }
        res["contacts"] = {
            role: (c.to_dict() if isinstance(c, ContactInfo) else c)
            for role, c in self.contacts.items()
        }
        return res


def parse_vcard(vcard_array):
    if not vcard_array or len(vcard_array) < 2:
        return {}
    properties = vcard_array[1]
    card = {}
    for prop in properties:
        if len(prop) < 4:
            continue
        name, params, _, val = prop[0], prop[1], prop[2], prop[3]
        if name == "fn":
            card["name"] = val
        elif name == "org":
            card["organization"] = "\n".join(val) if isinstance(val, list) else val
        elif name == "email":
            card["email"] = val
        elif name == "tel":
            tel_val = val
            if isinstance(val, str) and val.startswith("tel:"):
                tel_val = val[4:]
            card["phone"] = tel_val
        elif name == "adr":
            if isinstance(val, list):
                street_parts = []
                for idx in (0, 1, 2):
                    if idx < len(val) and val[idx]:
                        if isinstance(val[idx], list):
                            street_parts.extend([x for x in val[idx] if x])
                        else:
                            street_parts.append(str(val[idx]))
                card["street"] = "\n".join(street_parts)
                if len(val) > 3 and val[3]:
                    card["city"] = val[3]
                if len(val) > 4 and val[4]:
                    card["state"] = val[4]
                if len(val) > 5 and val[5]:
                    card["postalcode"] = val[5]

                country = ""
                if len(val) > 6 and val[6]:
                    country = val[6]
                elif params and "cc" in params:
                    country = params["cc"]
                if country:
                    card["country"] = country
            else:
                card["street"] = val
    return card


def map_rdap_to_whois(rdap_data):
    creation_dates = []
    expiration_dates = []
    updated_dates = []

    events = rdap_data.get("events", [])
    for event in events:
        action = event.get("eventAction")
        date_str = event.get("eventDate")
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str).replace(tzinfo=None)
            if action == "registration":
                creation_dates.append(dt)
            elif action == "expiration":
                expiration_dates.append(dt)
            elif action in ("last changed", "last update"):
                updated_dates.append(dt)
        except Exception:
            pass

    registrar = None
    emails = []
    contacts = {
        "registrant": None,
        "tech": None,
        "admin": None,
        "billing": None,
    }

    def process_entities(entity_list):
        nonlocal registrar
        for entity in entity_list:
            roles = entity.get("roles", [])
            handle = entity.get("handle")

            vcard_arr = entity.get("vcardArray")
            contact_dict = parse_vcard(vcard_arr) if vcard_arr else {}

            contact_obj = None
            if contact_dict or handle:
                contact_obj = ContactInfo(
                    handle=handle,
                    name=contact_dict.get("name"),
                    organization=contact_dict.get("organization"),
                    email=contact_dict.get("email"),
                    phone=contact_dict.get("phone"),
                    street=contact_dict.get("street"),
                    city=contact_dict.get("city"),
                    state=contact_dict.get("state"),
                    postalcode=contact_dict.get("postalcode"),
                    country=contact_dict.get("country"),
                )

            if contact_dict.get("email"):
                emails.append(contact_dict["email"])

            if "registrar" in roles and contact_dict.get("name"):
                registrar = [contact_dict["name"]]

            role_map = {
                "registrant": "registrant",
                "technical": "tech",
                "administrative": "admin",
                "billing": "billing",
            }
            for r in roles:
                mapped_role = role_map.get(r)
                if mapped_role and contact_obj:
                    contacts[mapped_role] = contact_obj

            if "entities" in entity:
                process_entities(entity["entities"])

    process_entities(rdap_data.get("entities", []))

    nameservers = []
    ns_list = rdap_data.get("nameservers", [])
    for ns in ns_list:
        ns_name = ns.get("ldhName")
        if ns_name:
            nameservers.append(ns_name.lower())

    domain_id = rdap_data.get("handle")
    if domain_id:
        domain_id = [domain_id]
    else:
        domain_id = [rdap_data.get("ldhName", "").lower()] if rdap_data.get("ldhName") else None
    status = rdap_data.get("status")

    whois_data = WhoisData(
        id=domain_id,
        status=status,
        creation_date=creation_dates or None,
        expiration_date=expiration_dates or None,
        updated_date=updated_dates or None,
        registrar=registrar,
        whois_server=None,
        nameservers=nameservers or None,
        emails=list(set(emails)) if emails else None,
        contacts=contacts,
        raw=[json.dumps(rdap_data)],
    )

    return whois_data.to_dict()


def get_domain_whois(domain, logger=None):
    try:
        url = f"https://rdap.org/domain/{domain}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        if res.status_code == 200:
            if logger:
                logger.info(f"Successfully fetched RDAP data for domain: {domain}")
            return map_rdap_to_whois(res.json())
        else:
            if logger:
                logger.warn(
                    f"RDAP lookup for {domain} returned HTTP {res.status_code}. Falling back to WHOIS."
                )
    except Exception as e:
        if logger:
            logger.warn(f"RDAP lookup for {domain} failed: {e}. Falling back to WHOIS.")

    if logger:
        logger.info(f"Falling back to classic WHOIS query for domain: {domain}")
    return whois_alt.get_whois(domain)
