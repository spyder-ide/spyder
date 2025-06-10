from importlib.metadata import version

from jupyter_server.auth.decorator import authorized
from jupyter_server.base.handlers import JupyterHandler
from tornado import web

from spyder_remote_services.services.envs_manager.handlers import (
    handlers as envs_manager_handlers,
)
from spyder_remote_services.services.files.handlers import (
    handlers as files_handlers,
)
from spyder_remote_services.services.environ.handler import (
    handlers as environ_handlers,
)


class VersionHandler(JupyterHandler):
    """Handler to return the version of the service."""

    auth_resource = "spyder-services"

    @web.authenticated
    @authorized
    def get(self):
        """Return the version of the service."""
        self.finish(version("spyder_remote_services"))


handlers = (
    envs_manager_handlers +
    files_handlers +
    environ_handlers +
    [(r"/version", VersionHandler)]
)
