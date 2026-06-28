import os

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    content = content.replace("MicrosoftGraphMailDelegatedConnector.MicrosoftGraphMailDelegatedConnector(", "MicrosoftGraphMailDelegatedConnector(")
    
    with open(filepath, 'w') as f:
        f.write(content)

fix_file('tests/test_microsoft_graph_mail_delegated_connector/test_microsoft_graph_mail_delegated_connector.py')
