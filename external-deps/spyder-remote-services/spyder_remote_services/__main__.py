import argparse

from spyder_remote_services.jupyter_server.serverapp import (
    get_running_server,
    launch_new_instance,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--jupyter-server', action='store_true', help="Start the Spyder's Jupyter server")
    parser.add_argument('--get-running-info', action='store_true', help="Get the running server info")
    args, rest = parser.parse_known_args(argv)
    if args.jupyter_server:
        launch_new_instance(rest)
    elif args.get_running_info:
        if info := get_running_server(as_str=True):
            print(info)
        else:
            print('No info found.')
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
