from http import HTTPStatus
import os

from jupyter_server.auth.decorator import authorized
from jupyter_server.base.handlers import JupyterHandler
import orjson
from tornado import web


class EnvVarsHandler(JupyterHandler):
    """Handler for environment variables."""

    auth_resource = "spyder-services"

    def write_json(self, data, status=HTTPStatus.OK):
        """Write JSON response."""
        self.set_status(status)
        self.set_header("Content-Type", "application/json")
        self.finish(orjson.dumps(data))

    def write_value(self, value, status=HTTPStatus.OK):
        """Write a value response."""
        self.set_status(status)
        self.set_header("Content-Type", "text/plain")
        self.finish(value)

    def finish_with_status(self, status):
        """Finish the request with a specific status."""
        self.set_status(status)
        self.finish()

    @web.authenticated
    @authorized
    def get(self, name=None):
        """Get the value of an environment variable."""
        if name is None:
            self.write_json(
                os.environ.copy(),
            )
            return
        value = os.environ.get(name)
        if value is None:
            raise web.HTTPError(
                HTTPStatus.NOT_FOUND, f"Environment variable {name} not found",
            )
        self.write_value(value)

    @web.authenticated
    @authorized
    def post(self, name):
        """Set the value of an environment variable."""
        value = self.get_body_argument("value")
        os.environ[name] = value
        self.finish_with_status(HTTPStatus.CREATED)

    @web.authenticated
    @authorized
    def delete(self, name):
        """Delete an environment variable."""
        if name in os.environ:
            del os.environ[name]
            self.finish_with_status(HTTPStatus.NO_CONTENT)
        else:
            raise web.HTTPError(
                HTTPStatus.NOT_FOUND, f"Environment variable {name} not found",
            )


_name_regex = r"(?P<name>.+)"

handlers = [
    (r"/environ", EnvVarsHandler),
    (rf"/environ/{_name_regex}", EnvVarsHandler),
]
