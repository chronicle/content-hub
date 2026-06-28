import os

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix relative imports that go beyond top-level package
    content = content.replace("from ..core", "from core")
    content = content.replace("from ..connectors", "from connectors")
    
    with open(filepath, 'w') as f:
        f.write(content)

for folder in ['actions', 'connectors', 'core']:
    if not os.path.exists(folder):
        continue
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith('.py'):
                fix_file(os.path.join(root, file))
