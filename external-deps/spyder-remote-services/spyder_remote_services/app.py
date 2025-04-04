"""Spyder server application."""

from contextlib import suppress
import os
import json
from pathlib import Path

from jupyter_core.application import JupyterApp
from jupyter_server.extension.application import ExtensionApp
from jupyter_server.serverapp import ServerApp
from traitlets import Bool, default
from jupyter_server.utils import check_pid
from jupyter_core.paths import jupyter_runtime_dir

from spyder_remote_services.services import handlers
from spyder_remote_services.services.spyder_kernels.patches import (
    patch_main_kernel_handler,
    patch_maping_kernel_manager,
)
from spyder_remote_services.utils import get_free_port


class SpyderServerApp(ServerApp):
    spyder_server_info_file = "jpserver-spyder.json"

    set_dynamic_port = Bool(
        True,
        help="""Set the port dynamically.

        Get an available port instead of using the default port
        if no port is provided.
        """,
    ).tag(config=True)

    open_browser = False
    no_browser_open_file = True

    @default("port")
    def _port_default(self):
        if self.set_dynamic_port:
            return get_free_port()
        return int(os.getenv(self.port_env, self.port_default_value))

    @property
    def info_file(self):
        return str(Path(self.runtime_dir) / self.spyder_server_info_file)

    def write_server_info_file(self, *, __pid_check=True) -> None:
        info_file = Path(self.info_file)
        if info_file.exists():
            if __pid_check:
                with info_file.open(mode="rb") as f:
                    info = json.load(f)

                # Simple check whether that process is really still running
                if ("pid" in info) and not check_pid(info["pid"]):
                    # If the process has died, try to delete its info file
                    with suppress(OSError):
                        info_file.unlink()
                    self.write_server_info_file(__pid_check=False)

            raise FileExistsError(
                f"Server info file {self.info_file} already exists."
                "Muliple servers are not supported, please make sure"
                "there is no other server running."
            )
        super().write_server_info_file()


class SpyderServerInfoApp(JupyterApp):
    description: str = "Show information about the currently running Spyder server."

    def start(self):
        """Start the server list application."""
        runtime_dir = Path(jupyter_runtime_dir())

        # The runtime dir might not exist
        if not runtime_dir.is_dir():
            return

        conf_file = runtime_dir / SpyderServerApp.spyder_server_info_file

        if not conf_file.exists():
            return

        with conf_file.open(mode="rb") as f:
            info = json.load(f)

        # Simple check whether that process is really still running
        # Also remove leftover files from IPython 2.x without a pid field
        if ("pid" in info) and check_pid(info["pid"]):
            print(json.dumps(info, indent=None))
        else:
            # If the process has died, try to delete its info file
            with suppress(OSError):
                conf_file.unlink()


class SpyderRemoteServices(ExtensionApp):
    """A simple jupyter server application."""

    # The name of the extension.
    name = "spyder-services"

    open_browser = False

    serverapp_class = SpyderServerApp

    subcommands = {
        "info": (SpyderServerInfoApp, SpyderServerInfoApp.description),
    }

    def initialize_handlers(self):
        """Initialize handlers."""
        self.handlers.extend([(rf"/{self.name}{h[0]}", h[1]) for h in handlers])

    def initialize(self):
        super().initialize()
        self.apply_patches()

    def apply_patches(self):
        patch_maping_kernel_manager(self.serverapp.kernel_manager)
        patch_main_kernel_handler(self.serverapp.web_app.default_router)


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------

main = launch_new_instance = SpyderRemoteServices.launch_instance
