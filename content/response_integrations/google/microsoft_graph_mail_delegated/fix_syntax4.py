import os

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    content = content.replace("integration_testing.common import create_entity", "from integration_testing.common import create_entity")
    content = content.replace("integration_testing.common import set_is_test_run_to", "from integration_testing.common import set_is_test_run_to")
    
    with open(filepath, 'w') as f:
        f.write(content)

for root, dirs, files in os.walk('tests'):
    for file in files:
        if file.endswith('.py'):
            fix_file(os.path.join(root, file))
