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

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import requests
import whois_alt
import whois_alt.parse as parse

# Monkeypatch whois_alt to prevent catastrophic backtracking on AFNIC (nic.fr) whois contacts.
safe_regexes = []
for r in parse.nic_contact_regexes:
    pattern = r.pattern
    if "type:\\s*(?P<type>.+)" in pattern and "contact:\\s*(?P<name>.+)" in pattern:
        pass
    else:
        safe_regexes.append(r)
parse.nic_contact_regexes = safe_regexes


def parse_afnic_contact_blocks(data: list[str]) -> list[dict[str, Any]]:
    """Parse AFNIC contact blocks to prevent catastrophic backtracking in whois_alt.

    Args:
        data: List of raw WHOIS text segments from AFNIC server.

    Returns:
        List of parsed contact dictionaries containing handle, type, name, etc.
    """
    handle_contacts = []
    for segment in data:
        blocks = segment.split("\n\n")
        for block in blocks:
            if "nic-hdl:" not in block:
                continue
            contact: dict[str, Any] = {}
            address_lines = []
            for line in block.splitlines():
                line = line.strip()
                if not line or ":" not in line:
                    continue
                key, val = line.split(":", 1)
                key = key.strip().lower()
                val = val.strip()
                if key == "nic-hdl":
                    contact["handle"] = val
                elif key == "type":
                    contact["type"] = val
                elif key == "contact":
                    contact["name"] = val
                elif key == "address":
                    address_lines.append(val)
                elif key == "country":
                    contact["country"] = val
                elif key == "phone":
                    contact["phone"] = val
                elif key == "fax-no":
                    contact["fax"] = val
                elif key == "e-mail":
                    contact["email"] = val
                elif key == "changed":
                    contact["changedate"] = val

            for idx, addr in enumerate(address_lines[:4]):
                contact[f"street{idx + 1}"] = addr

            if "handle" in contact:
                handle_contacts.append(contact)
    return handle_contacts


orig_parse_nic_contact = parse.parse_nic_contact


def my_parse_nic_contact(data: list[str]) -> list[dict[str, Any]]:
    """Augment parsed nic contacts with AFNIC contact blocks.

    Args:
        data: List of raw WHOIS text segments.

    Returns:
        List of combined and deduplicated contact dictionaries.
    """
    contacts = orig_parse_nic_contact(data)
    afnic_contacts = parse_afnic_contact_blocks(data)
    existing_handles = {c["handle"] for c in contacts if "handle" in c}
    for ac in afnic_contacts:
        if ac["handle"] not in existing_handles:
            contacts.append(ac)
            existing_handles.add(ac["handle"])
    return contacts


parse.parse_nic_contact = my_parse_nic_contact


class ContactInfo:
    """Model representing contact information for a domain registrant, admin, or tech contact."""

    def __init__(
        self,
        handle: str | None = None,
        name: str | None = None,
        organization: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        street: str | None = None,
        city: str | None = None,
        state: str | None = None,
        postalcode: str | None = None,
        country: str | None = None,
    ) -> None:
        """Initialize ContactInfo with contact details.

        Args:
            handle: Contact handle or ID.
            name: Contact name.
            organization: Contact organization name.
            email: Contact email address.
            phone: Contact phone number.
            street: Contact street address.
            city: Contact city.
            state: Contact state or province.
            postalcode: Contact postal or zip code.
            country: Contact country or country code.
        """
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

    def to_dict(self) -> dict[str, Any]:
        """Convert ContactInfo to a dictionary containing only non-None fields.

        Returns:
            Dictionary representation of contact info with None values omitted.
        """
        return {k: v for k, v in self.__dict__.items() if v is not None}


class WhoisData:
    """Model representing domain WHOIS/RDAP data matching classic WHOIS output format."""

    def __init__(
        self,
        id: list[str] | None = None,
        status: list[str] | str | None = None,
        creation_date: list[datetime] | None = None,
        expiration_date: list[datetime] | None = None,
        updated_date: list[datetime] | None = None,
        registrar: list[str] | None = None,
        whois_server: str | None = None,
        nameservers: list[str] | None = None,
        emails: list[str] | None = None,
        contacts: dict[str, ContactInfo | dict[str, Any] | None] | None = None,
        raw: list[str] | None = None,
    ) -> None:
        """Initialize WhoisData with domain attributes.

        Args:
            id: Domain ID or name list.
            status: Domain registration status list or string.
            creation_date: Domain creation / registration date(s).
            expiration_date: Domain expiration date(s).
            updated_date: Domain last updated date(s).
            registrar: Domain registrar list.
            whois_server: WHOIS server host name.
            nameservers: Domain name servers list.
            emails: Associated contact email list.
            contacts: Role-based contacts dictionary.
            raw: Raw RDAP or WHOIS payload list.
        """
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

    def to_dict(self) -> dict[str, Any]:
        """Convert WhoisData to dictionary format compatible with classic WHOIS schema.

        Returns:
            Dictionary representation of WHOIS domain data.
        """
        res: dict[str, Any] = {
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


def parse_vcard(vcard_array: list[Any] | None) -> dict[str, Any]:
    """Parse a jCard/vCard JSON array into a normalized contact dictionary.

    Args:
        vcard_array: Raw vCard array from RDAP entity representation.

    Returns:
        Dictionary containing parsed contact properties.
    """
    if not vcard_array or len(vcard_array) < 2:
        return {}
    properties = vcard_array[1]
    card: dict[str, Any] = {}
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


def map_rdap_to_whois(rdap_data: dict[str, Any]) -> dict[str, Any]:
    """Map RDAP JSON response to a dictionary compatible with whois-alt output.

    Args:
        rdap_data: Parsed JSON payload returned by an RDAP server.

    Returns:
        Normalized dictionary representing domain registration details.
    """
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
    emails: list[str] = []
    contacts: dict[str, ContactInfo | None] = {
        "registrant": None,
        "tech": None,
        "admin": None,
        "billing": None,
    }

    def process_entities(entity_list: list[dict[str, Any]]) -> None:
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
            nameservers.append(ns_name.upper())

    domain_id = rdap_data.get("handle")
    if domain_id:
        domain_id = [domain_id]
    else:
        domain_id = (
            [rdap_data.get("ldhName", "").lower()] if rdap_data.get("ldhName") else None
        )
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
        emails=list(dict.fromkeys(emails)) if emails else None,
        contacts=contacts,
        raw=[json.dumps(rdap_data)],
    )

    return whois_data.to_dict()


def get_domain_whois(domain: str, logger: Any = None) -> dict[str, Any]:
    """Retrieve domain WHOIS information via RDAP with fallback to classic WHOIS.

    Args:
        domain: Domain name to query.
        logger: Optional logger instance for logging informational or warning messages.

    Returns:
        Dictionary containing WHOIS/RDAP domain data.
    """
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
