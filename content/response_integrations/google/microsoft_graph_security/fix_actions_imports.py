import os

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix relative imports that go beyond top-level package
    content = content.replace("from ..core", "from core")
    
    with open(filepath, 'w') as f:
        f.write(content)

for root, dirs, files in os.walk('actions'):
    for file in files:
        if file.endswith('.py'):
            fix_file(os.path.join(root, file))
