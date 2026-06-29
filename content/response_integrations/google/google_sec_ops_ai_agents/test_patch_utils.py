import pytest
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.base.utils import create_soar_action

def test_triage():
    action = create_soar_action()
    print("Action type:", type(action))
