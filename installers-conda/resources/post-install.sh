#!/bin/bash -i
set -e
unset HISTFILE

echo "*** Running post install script for ${INSTALLER_NAME} ..."

echo "Args = $@"
echo "Environment variables:"
env | sort
echo ""

# ---- Sed options
# BSD sed requires extra "" after -i flag
if [[ $(sed --version 2>/dev/null) ]]; then
    # GNU sed has --version
    sed_opts=("-i" "-e")
else
    # BSD sed does not have --version
    sed_opts=("-i" "''" "-e")
fi

# ---- Shortcut
pythonexe=${PREFIX}/bin/python
menuinst=${PREFIX}/bin/menuinst_cli.py
mode=$([[ -e "${PREFIX}/.nonadmin" ]] && echo "user" || echo "system")
shortcut_path=$($pythonexe $menuinst shortcut --mode=$mode)

# ---- Aliases
spy_exe="${PREFIX}/envs/spyder-runtime/bin/spyder"
u_spy_exe="${PREFIX}/uninstall-spyder.sh"

[[ "$OSTYPE" == "linux"* ]] && alias_text="alias spyder=${spy_exe}"
[[ "$mode" == "user" ]] && alias_text="${alias_text:+${alias_text}\n}alias uninstall-spyder=${u_spy_exe}"

m1="# >>> Added by Spyder >>>"
m2="# <<< Added by Spyder <<<"

add_alias() {
    if [[ ! -s "$shell_init" ]]; then
        echo -e "$m1\n${alias_text}\n$m2" > $shell_init
        return
    fi

    # BSD sed does not like semicolons; newlines work for both BSD and GNU.
    sed ${sed_opts[@]} "
    /$m1/,/$m2/{
        h
        /$m2/ s|.*|$m1\n$alias_text\n$m2|
        t
        d
    }
    \${
        x
        /^$/{
            s||\n$m1\n$alias_text\n$m2|
            H
        }
        x
    }" $shell_init
}

if [[ "$mode" == "system" && "$OSTYPE" == "darwin"* ]]; then
    shell_init_list=("/etc/zshrc" "/etc/bashrc")
elif [[ "$mode" == "system" ]]; then
    shell_init_list=("/etc/zsh/zshrc" "/etc/bash.bashrc")
else
    shell_init_list=("$HOME/.zshrc" "$HOME/.bashrc")
fi

for shell_init in ${shell_init_list[@]}; do
    # If shell rc path or alias_text is empty, don't do anything
    [[ -z "$shell_init" || -z "$alias_text" ]] && continue

    # Don't create non-existent global init file
    [[ "$mode" == "system" && ! -f "$shell_init" ]] && continue

    echo "Creating aliases in $shell_init ..."
    add_alias
done

# ---- Uninstall script
echo "Creating uninstall script..."
cat <<END > ${u_spy_exe}
#!/bin/bash

if [[ ! -w ${PREFIX} || ! -w "$shortcut_path" ]]; then
    echo "Uninstalling Spyder requires sudo privileges."
    exit 1
fi

while getopts "f" option; do
    case "\$option" in
        (f) force=true ;;
    esac
done
shift \$((\$OPTIND - 1))

if [[ -z \$force ]]; then
    cat <<EOF
You are about to uninstall Spyder.
If you proceed, aliases will be removed from:
  ${shell_init_list[@]}
and the following will be removed:
  ${shortcut_path}
  ${PREFIX}

Do you wish to continue?
EOF
    read -p " [yes|NO]: " confirm
    confirm=\$(echo \$confirm | tr '[:upper:]' '[:lower:]')
    if [[ ! "\$confirm" =~ ^y(es)?$ ]]; then
        echo "Uninstall aborted."
        exit 1
    fi
fi

# Quit Spyder
echo "Quitting Spyder..."
if [[ "\$OSTYPE" == "darwin"* ]]; then
    osascript -e 'quit app "$(basename "$shortcut_path")"' 2>/dev/null
else
    pkill spyder 2>/dev/null
fi
sleep 1
while [[ \$(pgrep spyder 2>/dev/null) ]]; do
    echo "Waiting for Spyder to quit..."
    sleep 1
done

# Remove aliases from shell startup
for x in ${shell_init_list[@]}; do
    [[ ! -f "\$x" ]] && continue
    echo "Removing Spyder shell commands from \$x..."
    sed ${sed_opts[@]} "/$m1/,/$m2/d" \$x
done

# Remove shortcut and environment
echo "Removing Spyder shortcut and environment..."
$pythonexe $menuinst remove

rm -rf ${PREFIX}

echo "Spyder successfully uninstalled."
END
chmod +x ${u_spy_exe}

# ---- Linux post-install notes
if [[ "$OSTYPE" == "linux"* ]]; then
    cat <<EOF

###############################################################################
#                             !!! IMPORTANT !!!
###############################################################################
Spyder can be launched by standard methods in Gnome and KDE desktop
environments. It can also be launched from the command line on all Linux
distributions with the command:

$ spyder

EOF
    if [[ "$mode" == "system" ]]; then
        cat <<EOF
This command will only be available in new shell sessions.

To uninstall Spyder, run the following from the command line:

$ sudo $PREFIX/uninstall-spyder.sh

EOF
    else
        cat <<EOF
To uninstall Spyder, run the following from the command line:

$ uninstall-spyder

These commands will only be available in new shell sessions. To make them
available in this session, you must source your $shell_init file with:

$ source $shell_init

EOF
    fi
    cat <<EOF
###############################################################################

EOF
fi

echo "*** Post install script for ${INSTALLER_NAME} complete"

# ---- Launch Spyder
[[ -n "$CI" ]] && exit 0  # Running in CI, don't launch Spyder

echo "Launching Spyder now..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    launch_script=${TMPDIR:-$SHARED_INSTALLER_TEMP}/post-install-launch.sh
    echo "Creating post-install launch script $launch_script..."
    cat <<EOF > $launch_script
#!/bin/bash
while pgrep -fq Installer.app; do
    sleep 1
done
open -a "$shortcut_path"
EOF
    chmod +x $launch_script
    cat $launch_script

    nohup $launch_script &>/dev/null &
elif [[ -n "$(which gtk-launch)" ]]; then
    gtk-launch $(basename $shortcut_path)
else
    nohup $spy_exe &>/dev/null &
fi
