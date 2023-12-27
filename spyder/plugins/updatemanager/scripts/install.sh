#!/bin/bash -i

unset HISTFILE  # Do not write to history with interactive shell

while getopts "i:c:p:v:" option; do
    case "$option" in
        (i) install_exe=$OPTARG ;;
        (c) conda=$OPTARG ;;
        (p) prefix=$OPTARG ;;
        (v) spy_ver=$OPTARG ;;
    esac
done
shift $(($OPTIND - 1))

update_spyder(){
    $conda install -p $prefix -y spyder=$spy_ver
    read -p "Press any key to exit..."
}

launch_spyder(){
    if [[ "$OSTYPE" = "darwin"* ]]; then
        shortcut=/Applications/Spyder.app
        [[ "$prefix" = "$HOME"* ]] && open -a $HOME$shortcut || open -a $shortcut
    elif [[ -n "$(which gtk-launch)" ]]; then
        gtk-launch spyder_spyder
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
    [[ "$OSTYPE" = "darwin"* ]] && open $install_exe || sh $install_exe
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

if [[ -e "$conda" && -d "$prefix" && -n "$spy_ver" ]]; then
    update_spyder
    launch_spyder
elif [[ -e "$install_exe" ]]; then
    install_spyder
fi

if [[ "$OSTYPE" = "darwin"* ]]; then
    # Close the Terminal window that was opened for this process
    osascript -e 'tell application "Terminal" to close first window' &
fi
