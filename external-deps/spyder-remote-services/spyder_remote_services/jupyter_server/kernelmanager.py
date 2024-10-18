from jupyter_server.services.kernels.kernelmanager import (
    AsyncMappingKernelManager,
)
from jupyter_server._tz import isoformat
from traitlets import Unicode



class SpyderAsyncMappingKernelManager(AsyncMappingKernelManager):
    kernel_manager_class = 'spyder_remote_services.jupyter_client.manager.SpyderAsyncIOLoopKernelManager'

    default_kernel_name = Unicode(
        'spyder-kernel', help='The name of the default kernel to start'
    ).tag(config=True)

    def kernel_model(self, kernel_id):
        """Return a JSON-safe dict representing a kernel

        For use in representing kernels in the JSON APIs.
        """
        self._check_kernel_id(kernel_id)
        kernel = self._kernels[kernel_id]

        conn_info = kernel.get_connection_info()

        # convert key bytes to str
        conn_info["key"] = conn_info["key"].decode()

        model = {
            "id": kernel_id,
            "name": kernel.kernel_name,
            "last_activity": isoformat(kernel.last_activity),
            "execution_state": kernel.execution_state,
            "connections": self._kernel_connections.get(kernel_id, 0),
            "connection_info": conn_info,
        }
        if getattr(kernel, "reason", None):
            model["reason"] = kernel.reason
        return model
