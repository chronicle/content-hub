import pathlib


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
MOCK_DATA_FILE_NAME: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
INTEGRATION_PATH: pathlib.Path = (
    pathlib.Path(__file__).parent.parent.parent / "Integrations" / "Siemplify"
)
