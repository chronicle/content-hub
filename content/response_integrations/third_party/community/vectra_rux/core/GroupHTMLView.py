from __future__ import annotations

from .constants import GROUP_TYPE_FIELD_MAPPING


def render_group_object_as_html(group_obj, group_type):
    """Renders a given group object as an HTML string.

    Args:
        group_obj (dict): The group object to be rendered.
        group_type (str): The type of the group.

    Returns:
        str: The HTML string representation of the group object.

    """
    html_content = _get_html_header()
    response_content = ["id", "type", "name", "description", "importance", "members"]

    table_content = "".join(
        render_group_property(key, value, group_type)
        for key, value in group_obj.items()
        if key in response_content
    )

    html_content += f"""
    <table style="width: 50%; border-collapse: collapse; background-color: white; \
    box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-radius: 4px; overflow: hidden;">
        <thead>
            <tr>
                <th style="padding: 15px; text-align: left; background-color: #f8f9fa; \
                color: #333; font-weight: bold; text-transform: uppercase; \
                border-bottom: 2px solid #dee2e6;">
                    Property
                </th>
                <th style="padding: 15px; text-align: left; background-color: #f8f9fa;\
                color: #333; font-weight: bold; text-transform: uppercase; \
                border-bottom: 2px solid #dee2e6;">
                    Value
                </th>
            </tr>
        </thead>
        <tbody>
            {table_content}
        </tbody>
    </table>
    </body>
    </html>
    """

    return html_content


def render_group_property(property_key, property_value, group_type):
    """Renders a group property as an HTML string.

    Args:
        property_key (str): The property key.
        property_value (Any): The property value.
        group_type (str): The type of the group.

    Returns:
        str: The HTML string representation of the property.

    """
    if property_key == "members":
        property_value = property_value or []
        members_list = "".join(
            f"<li style='margin-bottom: 8px;'>{_get_member_value(member, group_type)}</li>"
            for member in property_value
        )
        return f"""<tr>
                <td style="padding: 12px 15px; text-align: left; \
                border-bottom: 1px solid #e9ecef;">{property_key.title()}</td>
                <td style="padding: 12px 15px; text-align: left; border-bottom: 1px solid #e9ecef;">
                    <ul style="margin: 0; padding-left: 20px; list-style-type: circle;">\
                    {members_list}
                        </ul>
                </td>
            </tr>"""

    return f"""<tr>
            <td style="padding: 12px 15px; text-align: left; border-bottom: 1px solid #e9ecef;">\
            {property_key.title()}</td>
            <td style="padding: 12px 15px; text-align: left; border-bottom: 1px solid #e9ecef;">\
            {property_value}</td>
        </tr>"""


def _get_member_value(member, group_type):
    """Helper function to get the member value based on the group type.

    Args:
        member (Any): The member object or value.
        group_type (str): The type of the group.

    Returns:
        str: The value of the member.

    """
    return (
        member
        if GROUP_TYPE_FIELD_MAPPING[group_type] == group_type
        else member.get(GROUP_TYPE_FIELD_MAPPING[group_type])
    )


def _get_html_header():
    """Helper function to get the initial HTML header content.

    Returns:
        str: The HTML header content.

    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Group Details</title>
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; margin: 0; \
    padding: 20px; color: #333;">
    """
