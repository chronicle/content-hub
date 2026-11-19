from __future__ import annotations
pytest_plugins = ("integration_testing.conftest",)
import sys
import os
import pkgutil
import importlib
import soar_sdk
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f'soar_sdk.{name}'] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

from collections import namedtuple

import pytest

from TIPCommon.base.utils import CreateSession

from zoho_desk.core.ZohoDeskApiManager import ZohoDeskApiClient
from zoho_desk.core.datamodels import IntegrationParameters
from zoho_desk.tests.common import CONFIG
from zoho_desk.tests.core.session import ZohoDeskSession
from zoho_desk.tests.core.zoho_desk import ZohoDesk
from integration_testing.common import use_live_api
from integration_testing.logger import Logger


Agent = namedtuple("Agent", "id name email")
Comment = namedtuple("Comment", "content commented_time")
Ticket = namedtuple(
    "Ticket", "created_time description id status subject ticket_number"
)

# pylint: disable=redefined-outer-name


@pytest.fixture
def zoho_desk() -> ZohoDesk:
    yield ZohoDesk()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    zoho_desk: ZohoDesk,
) -> ZohoDeskSession:
    session = ZohoDeskSession(zoho_desk)
    """Mock zoho desk scripts' session and get back an object to view request history"""

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
    yield session


@pytest.fixture
def zoho_desk_manager(script_session: ZohoDeskSession) -> ZohoDeskApiClient:
    """ZohoDesk manager"""
    api_root: str = CONFIG["API Root"]
    verify_ssl: bool = CONFIG["Verify SSL"]
    if isinstance(verify_ssl, str):
        verify_ssl = verify_ssl.lower() == "true"

    logger = Logger()
    ips: IntegrationParameters = IntegrationParameters(api_root, "", verify_ssl, logger)
    yield ZohoDeskApiClient(script_session, ips)


@pytest.fixture(scope="function")
def ticket_data() -> Ticket:
    """ZohoDesk Ticket"""
    ticket = Ticket(
        created_time="2022-08-12T10:12:02.000Z",
        description="fff",
        id="115142000000219090",
        status="Open",
        subject=(
            'abc def ghi jkl mno pqrs tuv wxyz ABC DEF GHI JKL MNO PQRS TUV WXYZ !"§ '
            "$%& /() =?* '<> #|; ²³~ @`´ ©«» ¤¼× {} abc def ghi jkl mno pqrs tuv wxyz "
            "ABC DEF GHI JKL MNO PQRS TUV WXYZ !\"§ $%& /() =?* '<> #|; ²³~ @`´ ©«» ¤¼×"
            " {} abc def ghi jkl mno pqrs tuv wxyz"
        ),
        ticket_number="126",
    )
    yield ticket


@pytest.fixture(scope="function")
def comment_data() -> Comment:
    """ZohoDesk Comment"""
    comment = Comment(
        content=(
            '<div style="font-size: 14px; font-family: LatoRegular, Regular, Lato, '
            '&quot;Lato 2&quot;, Arial, Helvetica, sans-serif"><div><span id="x_6286538'
            '4docs-internal-guid-db7bbb94-7fff-8c6a-af0c-dab621277131"><span style='
            '"font-size: 11pt; font-family: Arial; background-color: transparent; '
            "font-variant-numeric: normal; vertical-align: baseline; white-space: "
            'pre-wrap"><b><i><u><span class="x_62865384colour" style="color: '
            'rgb(255, 0, 119)"><span class="x_62865384highlight" style='
            '"background-color: rgb(204, 238, 255)"><div class="x_62865384target_moving'
            '"><div class="x_62865384KB_Editor_ImageDiscBdr" style="margin: 20px; borde'
            "r-radius: 3px; border: 1px solid rgb(238, 238, 238); display: inline-bloc "
            'k"id="x_62865384desc_img_14534151638440962"><img src="https://desk.zoho.eu'
            "/support/ImageDisplay?downloadType=uploadedFile&amp;fileName=1660119998639"
            ".gif&amp;blockId=ca76ab1c619f743bbc6f7e12498e75ce694c04ff76014da7&amp;zgId"
            '=1a991909fd6bebe5fc0f13afecbc8bcf&amp;mode=view" style="padding: 0px; max-'
            'width: 100%; box-sizing: border-box; width: 100px; height: auto" data-zde'
            'skdocid="img_14534151638440962" class="x_62865384docsimage" data-zdeskdo'
            'cselectedclass="original" /><span class="x_62865384KB_Editor_Quotedisc" '
            'style="position: relative; display: block; text-align: left; padding: 0p'
            'x 10px 10px; color: rgb(153, 153, 153)"><span class="x_62865384inner">pe'
            "rfect</span></span></div></div></span></span></u></i></b></span></span>"
            '</div><div><span id="x_62865384docs-internal-guid-df9bc435-7fff-351e-54a'
            'c-06388395fa1e"><span style="font-size: 11pt; font-family: Arial; backgro'
            "und-color: transparent; font-variant-numeric: normal; vertical-align: ba"
            "seline; white-space: pre-wrap\">$%#FYĐđצקЊกฃアィԱԳ😀🌍'&quot;’”‘’“”</sp"
            "an></span></div></div>"
        ),
        commented_time="2022-08-10T08:27:15.000Z",
    )
    yield comment


@pytest.fixture(scope="function")
def agent_data() -> Agent:
    """ZohoDesk Agent"""
    agent = Agent(id="115142000000092001", name="Milen", email="mivanov@siemplify.co")
    yield agent

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
