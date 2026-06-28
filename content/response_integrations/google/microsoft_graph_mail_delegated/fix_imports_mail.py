import os

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace legacy imports
    content = content.replace("Integrations.MicrosoftGraphMailDelegated.Managers", "core")
    content = content.replace("Integrations.MicrosoftGraphMailDelegated.ActionsScripts", "actions")
    content = content.replace("Integrations.MicrosoftGraphMailDelegated", "actions")
    content = content.replace("Tests.integrations.MicrosoftGraphMailDelegated.", "tests.")
    content = content.replace("from Tests.mocks.logger import Logger", "from integration_testing.logger import Logger")
    content = content.replace("from Tests.mocks.common import use_live_api", "")
    content = content.replace("from Tests.mocks", "integration_testing")
    content = content.replace("not use_live_api()", "True")
    
    with open(filepath, 'w') as f:
        f.write(content)

for root, dirs, files in os.walk('tests'):
    for file in files:
        if file.endswith('.py'):
            fix_file(os.path.join(root, file))
