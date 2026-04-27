from __future__ import annotations
PLACEHOLDER_START = "["
PLACEHOLDER_END = "]"


def transform_template_string(template, event):
    """
    Transform string containing template using event data
    :param template: {str} String containing template
    :param event: {dict} Case event
    :return: {str} Transformed string
    """
    index = 0

    while PLACEHOLDER_START in template[index:] and PLACEHOLDER_END in template[index:]:
        partial_template = template[index:]
        start, end = (
            partial_template.find(PLACEHOLDER_START) + len(PLACEHOLDER_START),
            partial_template.find(PLACEHOLDER_END),
        )
        substring = partial_template[start:end]
        value = event.get(substring) if event.get(substring) else ""
        template = template.replace(
            f"{PLACEHOLDER_START}{substring}{PLACEHOLDER_END}", value, 1
        )
        index = index + start + len(value)

    return template
