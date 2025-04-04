from functools import wraps
import json
from types import MethodType
from typing import Any, Callable, Dict, List, ParamSpec, Tuple, TypeVar
import uuid

from jupyter_client.manager import KernelManager
from jupyter_core.utils import ensure_async
from jupyter_server._tz import isoformat
from jupyter_server.auth.decorator import authorized
from jupyter_server.services.kernels.handlers import MainKernelHandler
from jupyter_server.services.kernels.kernelmanager import (
    AsyncMappingKernelManager,
)
from jupyter_server.utils import url_escape, url_path_join
from tornado import web
from tornado.routing import Router

from spyder_remote_services.services.spyder_kernels.provisioner import SpyderKernelProvisioner

try:
    from jupyter_client.jsonutil import json_default
except ImportError:
    from jupyter_client.jsonutil import date_default as json_default


T = TypeVar("T")
P = ParamSpec("P")

class SpyderMainKernelHandler(MainKernelHandler):
    @web.authenticated
    @authorized
    async def post(self):
        """Start a kernel."""
        km = self.kernel_manager
        model = self.get_json_body()
        if model is None:
            model = {"name": km.default_kernel_name}
        else:
            model.setdefault("name", km.default_kernel_name)

        kernel_id = await ensure_async(
            km.start_kernel(  # type:ignore[has-type]
                kernel_name=model["name"], path=model.get("path"),
                spyder_kernel=model.get("spyder_kernel", False)
            )
        )

        model = await ensure_async(km.kernel_model(kernel_id))
        location = url_path_join(self.base_url, "api", "kernels", url_escape(kernel_id))
        self.set_header("Location", location)
        self.set_status(201)
        self.finish(json.dumps(model, default=json_default))


def __kernel_model(self, kernel_id):
    """
    Return a JSON-safe dict representing a kernel

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


def __patch_async_start_kernel(func: Callable[P, T]):
    @wraps(func)
    async def wrapper(self: KernelManager, *args: P.args, **kw: P.kwargs) -> T:
        self.kernel_id = self.kernel_id or kw.pop("kernel_id", str(uuid.uuid4()))
        if kw.pop("spyder_kernel", False):
            self.provisioner = SpyderKernelProvisioner(
                kernel_id=self.kernel_id,
                kernel_spec=self.kernel_spec,
                parent=self,
            )
        return await func(*args, **kw)
    return wrapper


def _patch_kernel_manager(
    old_kernel_manager_factory: Callable[P, KernelManager]
) -> Callable[P, KernelManager]:
    @wraps(old_kernel_manager_factory)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> KernelManager:
        kernel_manager = old_kernel_manager_factory(*args, **kwargs)
        kernel_manager._async_pre_start_kernel = MethodType(
            __patch_async_start_kernel(kernel_manager._async_pre_start_kernel),
            kernel_manager,
        )
        return kernel_manager

    return wrapper


def patch_maping_kernel_manager(obj: AsyncMappingKernelManager):
    obj.kernel_model = MethodType(__kernel_model, obj)
    obj.default_kernel_name = "spyder-kernel"
    obj.kernel_manager_factory = _patch_kernel_manager(obj.kernel_manager_factory)


def patch_main_kernel_handler(router: Router):
    for idx, rule in enumerate(router.rules):
        if isinstance(rule.target, Router):
            patch_main_kernel_handler(rule.target)
        elif rule.target is MainKernelHandler:
            router.rules[idx].target = SpyderMainKernelHandler
            break
