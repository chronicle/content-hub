from __future__ import annotations

import pathlib
import tempfile
from typing import Callable, Dict

import jinja2

from TIPCommon.types import SingleJson
from scc_enterprise.core import desc_html_template
from scc_enterprise.core import desc_jwm_template
from scc_enterprise.core.SCCEnterpriseDatamodels import DescriptionOutputType


CreateDescFn = Callable[[SingleJson], str]
TemplateMapping = Dict[DescriptionOutputType, CreateDescFn]

TEMPLATE_NAME = "tmp_create_description_template.html"


def _render_description_template(parameters: SingleJson, template: str) -> str:
    """Create HTML description using a Jinja template

    Args:
        parameters (SingleJson): Parameters to render the template.
        template (str): The default template to use if the template file doesn't exist.

    Returns:
        SingleJson: The rendered template, raw and escaped
    """
    with tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).parent) as tmp_dir:
        temp_path = pathlib.Path(tmp_dir)
        template_file = temp_path / TEMPLATE_NAME
        template_file.write_text(template)

        jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(temp_path),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        stored_template = jinja_env.get_template(template_file.name)

        return stored_template.render(parameters)


def _create_html_description(template_params: SingleJson) -> str:
    return _render_description_template(
        parameters=template_params, template=desc_html_template.HTML_TEMPLATE
    )


def _create_jwm_description(template_params: SingleJson) -> str:
    return _render_description_template(
        parameters=template_params, template=desc_jwm_template.JWM_TEMPLATE
    )


_TEMPLATE_TYPE_TO_DESC_TYPE_MAP: TemplateMapping = {
    DescriptionOutputType.HTML: _create_html_description,
    DescriptionOutputType.JWM: _create_jwm_description,
}


def get_create_desc_fn(output_type: DescriptionOutputType) -> CreateDescFn:
    return _TEMPLATE_TYPE_TO_DESC_TYPE_MAP[output_type]
