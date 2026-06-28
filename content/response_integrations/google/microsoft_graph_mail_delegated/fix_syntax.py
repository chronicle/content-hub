import os

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix the missing 'from ' caused by naive replace
    content = content.replace("integration_testing import router", "from integration_testing import router")
    content = content.replace("integration_testing.request import MockRequest", "from integration_testing.requests.request import MockRequest")
    content = content.replace("integration_testing.response import MockResponse", "from integration_testing.requests.response import MockResponse")
    content = content.replace("integration_testing.session import MockSession, RouteFunction", "from integration_testing.requests.session import MockSession, RouteFunction")
    content = content.replace("integration_testing.platform.script_output import MockActionOutput", "from integration_testing.platform.script_output import MockActionOutput")
    content = content.replace("integration_testing.set_meta import set_metadata", "from integration_testing.set_meta import set_metadata")
    content = content.replace("from integration_testing.logger import Logger", "from integration_testing.logger import Logger")
    
    with open(filepath, 'w') as f:
        f.write(content)

for root, dirs, files in os.walk('tests'):
    for file in files:
        if file.endswith('.py'):
            fix_file(os.path.join(root, file))
