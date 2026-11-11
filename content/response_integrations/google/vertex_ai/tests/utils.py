import os


def create_test_attachment(path: str, attachment_name: str) -> str:
    """
    Create a test attachment

    Returns:
        str: path to created attachment
    """
    attachment_content = b"This is a test content"

    if not os.path.exists(path):
        os.makedirs(path)

    local_path = os.path.join(path, attachment_name)

    with open(local_path, "wb") as f:
        f.write(attachment_content)

    return local_path


def delete_test_attachments(path: str):
    """
    Delete test attachment

    Args:
        path (str): CSV of path to test attachments
    """
    for file in path.split(","):
        try:
            os.remove(file)
        except FileNotFoundError:
            # File not found
            pass
