import json
import os
from pathlib import Path

from jupyter_server.transutils import _i18n
from jupyter_server.utils import check_pid
from jupyter_core.paths import jupyter_runtime_dir
from jupyter_server.serverapp import ServerApp
from traitlets import Bool, default

from spyder_remote_services.jupyter_server.kernelmanager import (
    SpyderAsyncMappingKernelManager,
)
from spyder_remote_services.utils import get_free_port


SYPDER_SERVER_INFO_FILE = "jpserver-spyder.json"

class SpyderServerApp(ServerApp):
    kernel_manager_class = SpyderAsyncMappingKernelManager

    set_dynamic_port = Bool(
        True,
        help="""Set the port dynamically.

        Get an available port instead of using the default port
        if no port is provided.
        """,
    ).tag(config=True)

    @default("port")
    def port_default(self):
        if self.set_dynamic_port:
            return get_free_port()
        return int(os.getenv(self.port_env, self.port_default_value))

    @property
    def info_file(self):
        return str((Path(self.runtime_dir) /
                    SYPDER_SERVER_INFO_FILE).resolve())


def get_running_server(runtime_dir=None, log=None, *, as_str=False):
    """Iterate over the server info files of running Jupyter servers.

    Given a runtime directory, find jpserver-* files in the security directory,
    and yield dicts of their information, each one pertaining to
    a currently running Jupyter server instance.
    """
    if runtime_dir is None:
        runtime_dir = jupyter_runtime_dir()

    runtime_dir = Path(runtime_dir)

    # The runtime dir might not exist
    if not runtime_dir.is_dir():
        return None

    conf_file = runtime_dir / SYPDER_SERVER_INFO_FILE

    if not conf_file.exists():
        return None

    with conf_file.open(mode="rb") as f:
        info = json.load(f)

    # Simple check whether that process is really still running
    # Also remove leftover files from IPython 2.x without a pid field
    if ("pid" in info) and check_pid(info["pid"]):
        if as_str:
            return json.dumps(info, indent=None)
        return info

    # If the process has died, try to delete its info file
    try:
        conf_file.unlink()
    except OSError as e:
        if log:
            log.warning(_i18n("Deleting server info file failed: %s.") % e)


main = launch_new_instance = SpyderServerApp.launch_instance

if __name__ == '__main__':
    main()
