import os

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix the mistakes from previous replacements
    content = content.replace("from integration_testing.response import MockResponse", "from integration_testing.requests.response import MockResponse")
    content = content.replace("from integration_testing.session import MockSession, RouteFunction", "from integration_testing.requests.session import MockSession, RouteFunction")
    content = content.replace("from integration_testing.action import MockActionOutput", "from integration_testing.platform.script_output import MockActionOutput")
    
    with open(filepath, 'w') as f:
        f.write(content)

for root, dirs, files in os.walk('tests'):
    for file in files:
        if file.endswith('.py'):
            fix_file(os.path.join(root, file))
