import io
class XHTMLWriter:
    @staticmethod
    def write(rdf_handler, pretty=True):
        return io.BytesIO(b"<html>Mock HTML Content</html>")
