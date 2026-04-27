from __future__ import annotations
from .datamodels import *


class McAfeeMvisionEPOParser:
    def get_auth_token(self, raw_json):
        return f'{raw_json.get("token_type", "")} {raw_json.get("access_token", "")}'

    def get_items_json(self, raw_json):
        return self.get_data_json(raw_json).get("items", [])

    def get_total_items(self, raw_json):
        return self.get_data_json(raw_json).get("totalItems", 0)

    def build_siemplify_tag(self, tag_json):
        return Tag(raw_data=tag_json, tag_id=tag_json.get("id"))

    def get_data_json(self, raw_json):
        return raw_json.get("data", {})

    def build_siemplify_device(self, device_json):
        return Device(
            raw_data=device_json,
            group_name=device_json.get("group", {}).get("name"),
            host=device_json.get("properties", {}).get("hostname"),
            ip=device_json.get("properties", {}).get("ipaddress"),
            uuid=device_json.get("uuid"),
            products_installed=[
                self.build_siemplify_product_installed(product_installed_json)
                for product_installed_json in device_json.get("productsInstalled", [])
            ],
            device_id=device_json.get("id"),
            lastcommunicated=device_json.get("lastcommunicated"),
            managedState=device_json.get("managedState"),
            osplatform=device_json.get("properties", {}).get("osplatform"),
            operatingsystem=device_json.get("properties", {}).get("operatingsystem"),
            windowsdomain=device_json.get("properties", {}).get("windowsdomain"),
            dnsname=device_json.get("properties", {}).get("dnsname"),
            datversion=device_json.get("properties", {}).get("datversion"),
            username=device_json.get("properties", {}).get("username"),
            groups=device_json.get("group", {}).get("name"),
            tags=" ".join(tag.get("tagName") for tag in device_json.get("tags", [])),
        )

    def build_siemplify_product_installed(self, product_installed_json):
        return ProductsInstalled(
            raw_data=product_installed_json,
            product=product_installed_json.get("product"),
            version=product_installed_json.get("version"),
        )

    def build_siemplify_group(self, group_json):
        return Group(
            raw_data=group_json,
            id=group_json.get("id"),
            name=group_json.get("name"),
            description=group_json.get("description"),
        )

    def build_siemplify_endpoint(self, endpoint_json):
        return Endpoint(
            raw_data=endpoint_json,
            uuid=endpoint_json.get("uuid"),
            ipaddress=endpoint_json.get("properties", {}).get("ipaddress"),
            hostname=endpoint_json.get("properties", {}).get("hostname"),
            username=endpoint_json.get("properties", {}).get("username"),
        )

    def build_siemplify_tag_details(self, tag_json):
        return TagDetails(
            raw_data=tag_json,
            id=tag_json.get("id"),
            name=tag_json.get("name"),
            description=tag_json.get("description"),
        )
