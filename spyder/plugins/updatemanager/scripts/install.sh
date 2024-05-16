#!/bin/bash -i

unset HISTFILE  # Do not write to history with interactive shell

while getopts "i:c:p:" option; do
    case "$option" in
        (i) install_file=$OPTARG ;;
        (c) conda=$OPTARG ;;
        (p) prefix=$OPTARG ;;
    esac
done
shift $(($OPTIND - 1))

update_spyder(){
    $conda update -p $prefix -y --file $install_file
    read -p "Press return to exit..."
}

launch_spyder(){
    root=$(dirname $conda)
    pythonexe=$root/python
    menuinst=$root/menuinst_cli.py
    mode=$([[ -e "${prefix}/.nonadmin" ]] && echo "user" || echo "system")
    shortcut_path=$($pythonexe $menuinst shortcut --mode=$mode)

    if [[ "$OSTYPE" = "darwin"* ]]; then
        open -a $shortcut
    elif [[ -n "$(which gtk-launch)" ]]; then
        gtk-launch $(basename ${shortcut_path%.*})
    else
        nohup $prefix/bin/spyder &>/dev/null &
    fi
}

install_spyder(){
    # First uninstall Spyder
    uninstall_script="$prefix/../../uninstall-spyder.sh"
    if [[ -f "$uninstall_script" ]]; then
        echo "Uninstalling Spyder..."
        echo ""
        $uninstall_script
        [[ $? > 0 ]] && return
    fi

    # Run installer
    [[ "$OSTYPE" = "darwin"* ]] && open $install_file || sh $install_file
}

cat <<EOF
=========================================================
Updating Spyder
---------------

IMPORTANT: Do not close this window until it has finished
=========================================================

EOF

while [[ $(pgrep spyder 2> /dev/null) ]]; do
    echo "Waiting for Spyder to quit..."
    sleep 1
done

echo "Spyder quit."

if [[ -e "$conda" && -d "$prefix" ]]; then
    update_spyder
    launch_spyder
else
    install_spyder
fi

if [[ "$OSTYPE" = "darwin"* ]]; then
    # Close the Terminal window that was opened for this process
    osascript -e 'tell application "Terminal" to close first window' &
fi
