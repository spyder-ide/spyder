#!/usr/bin/env bash

# This script tests the installer for macOS and Linux on CI
# and will only install for the local user.

exit_status=0

install() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Stream install.log to stdout to view all log messages.
        tail -F /var/log/install.log & tail_id=$!
        trap "kill -s TERM $tail_id" EXIT

        installer -pkg $PKG_PATH -target CurrentUserHomeDirectory >/dev/null
    elif [[ "$OSTYPE" == "linux"* ]]; then
        $PKG_PATH -b
    fi
}

check_prefix() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        base_prefix=$(compgen -G $HOME/Library/spyder-*)
    elif [[ "$OSTYPE" == "linux"* ]]; then
        base_prefix=$(compgen -G $HOME/.local/spyder-*)
    fi

    if [[ -d "$base_prefix" ]]; then
        echo "\nContents of ${base_prefix}:"
        ls -al $base_prefix
    else
        echo "$base_prefix does not exist!"
        exit 1
    fi
}

check_uninstall() {
    if [[ -e "${base_prefix}/uninstall-spyder.sh" ]]; then
        echo -e "\nContents of ${base_prefix}/uninstall-spyder.sh:"
        cat $base_prefix/uninstall-spyder.sh
    else
        echo "${base_prefix}/uninstall-spyder.sh does not exist!"
        exit_status=1
    fi
}

check_shortcut() {
    pythonexe=${base_prefix}/bin/python
    menuinst=${base_prefix}/bin/menuinst_cli.py
    shortcut=$($pythonexe $menuinst shortcut --mode=user)
    if [[ -e "${shortcut}" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "\n${shortcut}/Contents/MacOS contents:"
            ls -al "${shortcut}/Contents/MacOS"
            echo -e "\n$shortcut/Contents/Info.plist contents:"
            cat "${shortcut}/Contents/Info.plist"
            script=$(compgen -G "${shortcut}/Contents/MacOS/spyder"*-script)
            echo -e "\n${script} contents:"
            cat "${script}"
        elif [[ "$OSTYPE" == "linux"* ]]; then
            echo -e "\n${shortcut} contents:"
            cat $shortcut
        fi
    else
        echo "$shortcut does not exist"
        exit_status=1
    fi
}

install
echo "Install info:"
check_prefix
check_uninstall
check_shortcut

exit $exit_status
