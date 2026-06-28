import os

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace general integration_testing imports
    content = content.replace("from Tests.mocks import router", "from integration_testing import router")
    content = content.replace("from Tests.mocks.request import MockRequest", "from integration_testing.request import MockRequest")
    content = content.replace("from Tests.mocks.response import MockResponse", "from integration_testing.response import MockResponse")
    content = content.replace("from Tests.mocks.session import MockSession, RouteFunction", "from integration_testing.session import MockSession, RouteFunction")
    content = content.replace("from Tests.mocks.platform.script_output import MockActionOutput", "from integration_testing.action import MockActionOutput")
    content = content.replace("from Tests.mocks.set_meta import set_metadata", "from integration_testing.set_meta import set_metadata")
    content = content.replace("from Tests.mocks.product import MockProduct", "MockProduct = object")
    
    with open(filepath, 'w') as f:
        f.write(content)

for root, dirs, files in os.walk('tests'):
    for file in files:
        if file.endswith('.py'):
            fix_file(os.path.join(root, file))
