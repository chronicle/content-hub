import pathlib

from TIPCommon.types import SingleJson

from okta.tests.common import get_json_file_content

USER_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/user_response.json"
)
