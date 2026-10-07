import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app as flask_app  # noqa: E402


class StripPrefix:
    """Vercelは全パスをこの関数に回すので /api/index を取り除いて渡す。"""

    def __init__(self, wsgi):
        self.wsgi = wsgi

    def __call__(self, environ, start_response):
        p = environ.get("PATH_INFO", "")
        if p == "/api/index" or p == "/api/index/":
            environ["PATH_INFO"] = "/"
        elif p.startswith("/api/index/"):
            environ["PATH_INFO"] = p[len("/api/index"):]
        return self.wsgi(environ, start_response)


app = StripPrefix(flask_app.wsgi_app)
