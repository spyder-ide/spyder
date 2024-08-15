#!/bin/bash -i

unset HISTFILE  # Do not write to history with interactive shell

while getopts "i:c:p:r" option; do
    case "$option" in
        (i) install_file=$OPTARG ;;
        (c) conda=$OPTARG ;;
        (p) prefix=$OPTARG ;;
        (r) rebuild=true ;;
    esac
done
shift $(($OPTIND - 1))

update_spyder(){
    # Unzip installer file
    pushd $(dirname $install_file)

    # Determine OS type
    [[ "$OSTYPE" = "darwin"* ]] && os=osx || os=linux
    [[ "$(arch)" = "arm64" ]] && os=${os}-arm64 || os=${os}-64

    echo "Updating Spyder base environment..."
    $conda update --name base --yes --file "conda-base-${os}.lock"

    if [[ -n "$rebuild" ]]; then
        echo "Rebuilding Spyder runtime environment..."
        $conda remove --prefix $prefix --all --yes
        mkdir -p $prefix/Menu
        touch $prefix/Menu/conda-based-app
        conda_cmd=create
    else
        echo "Updating Spyder runtime environment..."
        conda_cmd=update
    fi
    $conda $conda_cmd --prefix $prefix --yes --file "conda-runtime-${os}.lock"

    echo "Cleaning packages and temporary files..."
    $conda clean --yes --packages --tempfiles $prefix
}

launch_spyder(){
    root=$(dirname $conda)
    pythonexe=$root/python
    menuinst=$root/menuinst_cli.py
    mode=$([[ -e "${prefix}/.nonadmin" ]] && echo "user" || echo "system")
    shortcut_path=$($pythonexe $menuinst shortcut --mode=$mode)

    if [[ "$OSTYPE" = "darwin"* ]]; then
        open -a "$shortcut_path"
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
    read -p "Press return to exit and launch Spyder..."
    launch_spyder
else
    install_spyder
fi

if [[ "$OSTYPE" = "darwin"* ]]; then
    # Close the Terminal window that was opened for this process
    osascript -e 'tell application "Terminal" to close first window' &
fi
