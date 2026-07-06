path = "/Users/haggit/PycharmProjects/marketplace/content/response_integrations/google/gmail/tests/conftest.py"
with open(path, "r") as f:
    content = f.read()

# First, remove the old mock_google_adc fixture entirely
import re
content = re.sub(r'\n@pytest\.fixture\(autouse=True\)\ndef mock_google_adc\(mocker\):.*?(?=\n\n|$)', '', content, flags=re.DOTALL)

# Also remove any stranded try/except mocker.patch calls at the bottom if they exist
content = re.sub(r'\n    mocker\.patch\("TIPCommon.*?\n        pass\n', '', content, flags=re.DOTALL)

# Now, right after sys.path.insert, add the global patches
insert_pos = content.find("sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))")
end_pos = content.find("\n", insert_pos) + 1

patch_code = """
import unittest.mock
_mock_creds = unittest.mock.Mock()
_mock_creds.universe_domain = "googleapis.com"
_patcher1 = unittest.mock.patch("google.auth.default", return_value=(_mock_creds, "test-project"))
_patcher2 = unittest.mock.patch("TIPCommon.rest.auth.get_adc", return_value=(_mock_creds, "test-project"))
_patcher1.start()
_patcher2.start()

"""

# Also patch HistoryRecordsList to fix the soar_sdk typing bug!
patch_code += """
from integration_testing.aiohttp.session import HistoryRecordsList
_original_hrl_init = HistoryRecordsList.__init__
def _patched_hrl_init(self, *args):
    if len(args) == 1 and isinstance(args[0], list):
        args = tuple(args[0])
    _original_hrl_init(self, *args)
HistoryRecordsList.__init__ = _patched_hrl_init

"""

content = content[:end_pos] + patch_code + content[end_pos:]

with open(path, "w") as f:
    f.write(content)
