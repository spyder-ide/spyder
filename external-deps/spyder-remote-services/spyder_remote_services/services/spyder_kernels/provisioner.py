from __future__ import annotations
import os
from typing import TYPE_CHECKING, Any

from jupyter_client.connect import LocalPortCache
from jupyter_client.localinterfaces import is_local_ip, local_ips
from jupyter_client.provisioning.local_provisioner import LocalProvisioner
from jupyter_client.provisioning.factory import KernelProvisionerFactory


if TYPE_CHECKING:
    from jupyter_client.manager import KernelManager


class SpyderKernelProvisioner(LocalProvisioner):
    """
    :class:`SpyderKernelProvisioner` is a kernel provisioner that is used to provision
    spyder-kernels for the Spyder IDE.
    """

    async def pre_launch(self, **kwargs: Any) -> dict[str, Any]:
        """
        Perform any steps in preparation for kernel process launch.

        This includes applying additional substitutions to the kernel launch command and env.
        It also includes preparation of launch parameters.

        Returns the updated kwargs.
        """

        # This should be considered temporary until a better division of labor can be defined.
        km: KernelManager = self.parent
        if km:
            if km.transport == "tcp" and not is_local_ip(km.ip):
                msg = (
                    "Can only launch a kernel on a local interface. "
                    f"This one is not: {km.ip}."
                    "Make sure that the '*_address' attributes are "
                    "configured properly. "
                    f"Currently valid addresses are: {local_ips()}"
                )
                raise RuntimeError(msg)
            # build the Popen cmd
            extra_arguments = kwargs.pop("extra_arguments", [])

            # write connection file / get default ports
            # TODO - change when handshake pattern is adopted
            if km.cache_ports and not self.ports_cached:
                lpc = LocalPortCache.instance()
                km.shell_port = lpc.find_available_port(km.ip)
                km.iopub_port = lpc.find_available_port(km.ip)
                km.stdin_port = lpc.find_available_port(km.ip)
                km.hb_port = lpc.find_available_port(km.ip)
                km.control_port = lpc.find_available_port(km.ip)
                self.ports_cached = True
            if kwargs.get("env"):
                jupyter_session = kwargs["env"].get("JPY_SESSION_NAME", "")
                km.write_connection_file(jupyter_session=jupyter_session)
            else:
                km.write_connection_file()
            self.connection_info = km.get_connection_info()

            kernel_cmd = km.format_kernel_cmd(
                extra_arguments=extra_arguments
            )  # This needs to remain here for b/c
        else:
            extra_arguments = kwargs.pop("extra_arguments", [])
            kernel_cmd = self.kernel_spec.argv + extra_arguments

        kwargs["env"] = {
            **os.environ.copy(),
            **kwargs.get("env", {}),
        }

        # Replace the `ipykernel_launcher` with `spyder_kernel.console`
        cmd_indx = kernel_cmd.index("ipykernel_launcher")
        if cmd_indx != -1:
            kernel_cmd[cmd_indx] = "spyder_kernels.console"

        return await super(LocalProvisioner, self).pre_launch(cmd=kernel_cmd, **kwargs)

    def _finalize_env(self, env: dict[str, str]) -> None:
        """Finalize the environment variables for the kernel."""
        # disable file validation for pydevd
        # this is needed for spyder-kernels to work with pydevd
        env["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
        return super()._finalize_env(env)
