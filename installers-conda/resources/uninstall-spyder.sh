#!/bin/bash

# Variables set at install time
PREFIX=__PREFIX__
mode=__MODE__
shell_init_list=__SHELL_INIT_LIST__
m1="__M1__"
m2="__M2__"
pythonexe=__PYTHONEXE__
menuinst=__MENUINST__

# Shortcuts
spyder_menu=${PREFIX}/envs/spyder-runtime/Menu/spyder-menu.json
uninstall_menu=${PREFIX}/Menu/uninstall-menu.json
shortcut_path="$($pythonexe $menuinst shortcut --mode=$mode --menu=$spyder_menu)"
shortcut_uninstall_path="$($pythonexe $menuinst shortcut --mode=$mode --menu=$uninstall_menu)"

if [[ ! -w ${PREFIX} || ! -w "${shortcut_path}" ]]; then
    echo "Uninstalling Spyder requires sudo privileges."
    exit 1
fi

while getopts "f" option; do
    case "$option" in
        (f) force=true ;;
    esac
done
shift $(($OPTIND - 1))

if [[ -z $force ]]; then
    cat <<EOF
You are about to uninstall Spyder.
If you proceed, aliases will be removed from:
  ${shell_init_list[0]}
  ${shell_init_list[1]}
and the following will be removed:
  ${shortcut_path}
  ${shortcut_uninstall_path}
  ${PREFIX}

Do you wish to continue?
EOF
    read -p " [yes|NO]: " confirm
    confirm=$(echo $confirm | tr '[:upper:]' '[:lower:]')
    if [[ ! "$confirm" =~ ^y(es)?$ ]]; then
        echo "Uninstall aborted."
        exit 1
    fi
fi

# Quit Spyder
echo "Quitting Spyder..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "quit app \"${shortcut_path}\"" 2>/dev/null
else
    pkill spyder 2>/dev/null
fi
sleep 1
while [[ $(pgrep spyder 2>/dev/null) ]]; do
    echo "Waiting for Spyder to quit..."
    sleep 1
done

# Remove aliases from shell startup
for x in ${shell_init_list[@]}; do
    # Resolve possible symlink
    [[ ! -f "$x" ]] && continue || x=$(readlink -f $x)

    echo "Removing Spyder shell commands from $x..."
    sed -i.bak -e "/$m1/,/$m2/d" $x
    rm $x.bak
done

# Remove shortcut and environment
echo "Removing Spyder shortcuts and environment..."
$pythonexe $menuinst remove --menu=${spyder_menu}
$pythonexe $menuinst remove --menu=${uninstall_menu}

rm -rf ${PREFIX}

echo "Spyder successfully uninstalled."
