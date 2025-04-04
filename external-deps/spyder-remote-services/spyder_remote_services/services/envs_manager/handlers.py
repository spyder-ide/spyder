from jupyter_server.auth.decorator import authorized
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.extension.handler import ExtensionHandlerMixin
import tornado
from tornado import web
from tornado.escape import json_decode

from envs_manager.manager import Manager, DEFAULT_BACKEND, DEFAULT_ENVS_ROOT_PATH, EXTERNAL_EXECUTABLE


class BaseEnvironmentHandler(ExtensionHandlerMixin, JupyterHandler):
    def prepare(self):
        if self.request.headers["Content-Type"] == "application/x-json":
            self.args = json_decode(self.request.body)


class ListEnviroments(BaseEnvironmentHandler):
    @tornado.web.authenticated
    def get(self,
            backend=DEFAULT_BACKEND,
            root_path=DEFAULT_ENVS_ROOT_PATH,
            external_executable=EXTERNAL_EXECUTABLE):
        return Manager.list_environments(backend, root_path, external_executable)

class CreateEnvironment(BaseEnvironmentHandler):

    @tornado.web.authenticated
    def post(self, backend, env_name):
        manager = Manager(
            backend=backend,
            env_name=env_name,
            **self.args.get("manager", {})
        )
        return manager.create_environment(
            packages=self.args.get("packages", ["Python"]),
            channels=self.args.get("channels"),
            force=self.args.get("force", False)
        )

class DeleteEnvironment(BaseEnvironmentHandler):

    @tornado.web.authenticated
    def delete(self, backend, env_name):
        manager = Manager(
            backend=backend,
            env_name=env_name,
            **self.args.get("manager", {})
        )
        return manager.delete_environment(
            force=self.args.get("force", False)
        )

class InstallPackages(BaseEnvironmentHandler):

    @tornado.web.authenticated
    def post(self, backend, env_name):
        manager = Manager(
            backend=backend,
            env_name=env_name,
            **self.args.get("manager", {})
        )
        return manager.install(
            packages=self.args.get("packages", None),
            channels=self.args.get("channels", None),
            force=self.args.get("force", False)
        )

class UninstallPackages(BaseEnvironmentHandler):

    @tornado.web.authenticated
    def delete(self, backend, env_name):
        manager = Manager(
            backend=backend,
            env_name=env_name,
            **self.args.get("manager", {})
        )
        return manager.uninstall(
            packages=self.args["packages"],
            force=self.args.get("force", False)
        )

class UpdatePackages(BaseEnvironmentHandler):

    @tornado.web.authenticated
    def put(self, backend, env_name):
        manager = Manager(
            backend=backend,
            env_name=env_name,
            **self.args.get("manager", {})
        )
        return manager.update(
            packages=self.args["packages"],
            force=self.args.get("force", False)
        )

class ListPackages(BaseEnvironmentHandler):

    @tornado.web.authenticated
    def get(self, backend, env_name):
        manager = Manager(
            backend=backend,
            env_name=env_name,
            **self.args.get("manager", {})
        )
        return manager.list()


# class ActivateEnvironment(BaseEnvironmentHandler):

#         @tornado.web.authenticated
#         def post(self, backend, env_name):
#             manager = Manager(
#                 backend=backend,
#                 env_name=env_name,
#                 **self.args.get("manager", {})
#             )
#             return manager.activate()


# class DeactivateEnvironment(BaseEnvironmentHandler):

#     @tornado.web.authenticated
#     def post(self, backend, env_name):
#         manager = Manager(
#             backend=backend,
#             env_name=env_name,
#             **self.args.get("manager", {})
#         )
#         return manager.deactivate()

_env_name_regex = r"(?P<env_name>\w+)"
_backend_regex = r"(?P<backend>\w+)"

handlers = [
    (r"/envs-manager/list-environments", ListEnviroments),
    (rf"/envs-manager/create-environment/{_backend_regex}/{_env_name_regex}", CreateEnvironment),
    (rf"/envs-manager/delete-environment/{_backend_regex}/{_env_name_regex}", DeleteEnvironment),
    (rf"/envs-manager/install-packages/{_backend_regex}/{_env_name_regex}", InstallPackages),
    (rf"/envs-manager/uninstall-packages/{_backend_regex}/{_env_name_regex}", UninstallPackages),
    (rf"/envs-manager/update-packages/{_backend_regex}/{_env_name_regex}", UpdatePackages),
    (rf"/envs-manager/list-packages/{_backend_regex}/{_env_name_regex}", ListPackages),
    # (rf"/envs-manager/activate-environment/{_backend_regex}/{_env_name_regex}", ActivateEnvironment),
    # (rf"/envs-manager/deactivate-environment/{_backend_regex}/{_env_name_regex}", DeactivateEnvironment),
]
