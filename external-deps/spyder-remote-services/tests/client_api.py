import requests

from jupyter_server.serverapp import list_running_servers


class Session(requests.Session):
    """Class to handle authentication with Jupyter Server.
    
    This class represents a session to communicate with a Jupyter Server.
    It automatically handles the authentication with the current running
    server and sets the headers, main URL, port and host.
    """
    def __init__(self, host=None, port=None, token=None):
        running_servers = list_running_servers()
        base_url = None
        if token:
            for server in running_servers:
                if server["token"] == token:
                    base_url = server["url"]
                    break
        elif host and port:
            for server in running_servers:
                if server["host"] == host and server["port"] == port:
                    token = server["token"]
                    base_url = server["url"]
                    break
        elif host:
            for server in running_servers:
                if server["host"] == host:
                    token = server["token"]
                    base_url = server["url"]
                    break
        elif port:
            for server in running_servers:
                if server["port"] == port:
                    token = server["token"]
                    base_url = server["url"]
                    break
        elif token is None and host is None and port is None:
            *_, server = running_servers
            token = server["token"]
            base_url = server["url"]

        self.base_url = base_url or f"http://{host}:{port}/"
        super().__init__()
        self.headers.update({"Authorization": f"token {token}"})

    def get(self, url, **kwargs):
        return super().get(self.base_url + url, **kwargs)

    def post(self, url, **kwargs):
        return super().post(self.base_url + url, **kwargs)

    def put(self, url, **kwargs):
        return super().put(self.base_url + url, **kwargs)

    def delete(self, url, **kwargs):
        return super().delete(self.base_url + url, **kwargs)
