from spyder_remote_services.services.envs_manager.handlers import handlers as envs_manager_handlers
from spyder_remote_services.services.fsspec.handlers import handlers as fsspec_handlers

handlers = envs_manager_handlers + fsspec_handlers
