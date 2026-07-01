import email
from email.message import Message

def text_to_utf8(text):
    if isinstance(text, bytes):
        return text.decode('utf-8', errors='replace')
    return str(text)

class MetaData:
    def __init__(self, msg: Message):
        self.msg = msg

    def to_dict(self):
        result = {}
        for key, value in self.msg.items():
            result[key] = text_to_utf8(value)
            
        # extract body
        body = ""
        html_body = ""
        if self.msg.is_multipart():
            for part in self.msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            decoded = payload.decode('utf-8', errors='replace')
                            if content_type == "text/plain":
                                body += decoded
                            elif content_type == "text/html":
                                html_body += decoded
                    except Exception:
                        pass
        else:
            try:
                payload = self.msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='replace')
            except Exception:
                pass
                
        result["body"] = body
        result["html_body"] = html_body
        return result
