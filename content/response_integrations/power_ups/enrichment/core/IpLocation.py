# Copyright 2025 Google LLC
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
from urllib.parse import quote

import geocoder
import requests


class IpLocation:
    """Model for storing location of given IP address.
    This class provides the following attributes:
    .. attribute:: ip_address
      IP address.
    .. attribute:: city
      City where IP address is located.
    .. attribute:: region
      Region where IP address is located.
    .. attribute:: country
      Country where IP address is located (two letters country code).
    .. attribute:: latitude
      Latitude where IP address is located.
    .. attribute:: longitude
      Longitude where IP address is located.
    """

    _ip_address = None
    _city = None
    _region = None
    _country = None
    _latitude = None
    _longitude = None

    def __init__(
        self,
        ip_address,
        city=None,
        region=None,
        country=None,
        latitude=None,
        longitude=None,
    ):
        self.ip_address = ip_address
        self.city = city
        self.region = region
        self.country = country
        self.latitude = latitude
        self.longitude = longitude

    @property
    def ip_address(self):
        return self._ip_address

    @ip_address.setter
    def ip_address(self, value):
        self._ip_address = value

    @property
    def city(self):
        return self._city

    @city.setter
    def city(self, value):
        self._city = value

    @property
    def region(self):
        return self._region

    @region.setter
    def region(self, value):
        self._region = value

    @property
    def country(self):
        return self._country

    @country.setter
    def country(self, value):
        self._country = value

    @property
    def latitude(self):
        return self._latitude

    @latitude.setter
    def latitude(self, value):
        self._latitude = value

    @property
    def longitude(self):
        return self._longitude

    @longitude.setter
    def longitude(self, value):
        self._longitude = value

    def to_json(self):
        return json.dumps(self.__dict__).replace('"_', '"')

    def to_csv(self, delimiter):
        return delimiter.join(str(self).split("\n"))

    def __str__(self):
        return f"{self.ip_address}\n{self.city}\n{self.region}\n{self.country}\n{self.latitude}\n{self.longitude}"

    def __repr__(self):
        return f"{self.__module__}.{self.__class__.__name__}({self.ip_address})"


class DbIpCity:
    """Class for accessing geolocation data provided by https://db-ip.com/api/."""

    @staticmethod
    def get(ip_address, api_key="free", db_path=None, username=None, password=None):
        # process request
        request = requests.get(
            "https://api.db-ip.com/v2/" + quote(api_key) + "/" + quote(ip_address),
            timeout=62,
        )

        # check for HTTP errors
        if request.status_code != 200:
            raise

        # parse content
        content = request.content.decode("utf-8")
        content = json.loads(content)

        # check for errors
        if content.get("error"):
            if content["error"] == "invalid address" or content["error"] == "invalid API key":
                raise
            raise
        # prepare return value

        ip_location = IpLocation(ip_address)

        # format data
        ip_location.country = content.get("countryCode")
        ip_location.region = content.get("stateProv")
        ip_location.city = content.get("city")

        # get lat/lon from OSM
        osm = geocoder.osm(
            content.get("city", "") + ", " + content.get("stateProv", "") + " " + content.get("countryCode", ""),
            timeout=62,
        )
        if osm.ok:
            osm = osm.json
            ip_location.latitude = float(osm["lat"])
            ip_location.longitude = float(osm["lng"])
        else:
            osm = geocoder.osm(
                content.get("city", "") + ", " + content.get("countryCode", ""),
                timeout=62,
            )
            if osm.ok:
                osm = osm.json
                ip_location.latitude = float(osm["lat"])
                ip_location.longitude = float(osm["lng"])
            else:
                ip_location.latitude = None
                ip_location.longitude = None
        return ip_location
