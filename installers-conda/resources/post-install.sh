#!/bin/bash -i
set -e
unset HISTFILE

echo "*** Running post install script for ${INSTALLER_NAME} ..."

echo "Args = $@"
echo "Environment variables:"
env | sort
echo ""

# ---- QtWebengine
# QtWebengine cannot find $prefix/resources directory on a APFS case-sensitive file system.
# This is not the default macOS file system. To work-around this we rename it to Resources.
# See https://github.com/spyder-ide/spyder/issues/23415
runtime_env="${PREFIX}/envs/spyder-runtime"
if [[ "$OSTYPE" == "darwin"* && ! -e "${runtime_env}/Resources" ]]; then
    # macOS and case-sensitive
    mv -f ${runtime_env}/resources ${runtime_env}/Resources || true
fi

# ---- Shortcut
pythonexe=${PREFIX}/bin/python
menuinst=${PREFIX}/bin/menuinst_cli.py
mode=$([[ -e "${PREFIX}/.nonadmin" ]] && echo "user" || echo "system")
spyder_menu=${PREFIX}/envs/spyder-runtime/Menu/spyder-menu.json
uninstall_menu=${PREFIX}/Menu/uninstall-menu.json
shortcut_path="$($pythonexe $menuinst shortcut --mode=$mode --menu=$spyder_menu)"
shortcut_uninstall_path="$($pythonexe $menuinst shortcut --mode=$mode --menu=$uninstall_menu)"

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
    sed -i.bak -e "
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
    rm $shell_init.bak
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

    # Resolve possible symlink
    [[ -f $shell_init ]] && shell_init=$(readlink -f $shell_init)

    echo "Creating aliases in $shell_init ..."
    add_alias
done

# ---- Uninstall
echo "Updating uninstall script..."
sed -i.bak \
    -e "s|__PREFIX__|${PREFIX}|g" \
    -e "s|__MODE__|${mode}|g" \
    -e "s|__SHELL_INIT_LIST__|(${shell_init_list[*]/#/ } )|g" \
    -e "s|__M1__|${m1}|g" \
    -e "s|__M2__|${m2}|g" \
    -e "s|__PYTHONEXE__|${pythonexe}|g" \
    -e "s|__MENUINST__|${menuinst}|g" \
    ${u_spy_exe}
chmod +x ${u_spy_exe}
rm ${u_spy_exe}.bak

# Create shortcut for the uninstaller
$pythonexe $menuinst install --target=${PREFIX} --menu=$uninstall_menu

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
To uninstall Spyder, open the application "Spyder ${INSTALLER_VER%%.} Uninstaller",
or run the following from the command line:

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
if [[
    -n "$CI"                                  # Running in CI (sh)
    || "$INSTALLER_UNATTENDED" == "1"         # Running in batch mode (sh)
    || "$COMMAND_LINE_INSTALL" == "1"         # Running in batch mode (pkg)
    || "$START_SPYDER" == "False"             # Running from updater (sh)
    || -f "$PACKAGE_PATH/../no-start-spyder"  # Running from updater (pkg)
]]; then
    echo "Not launching Spyder"
    exit 0
fi

echo "Launching Spyder after install completed."
if [[ "$OSTYPE" == "darwin"* ]]; then
    launch_script=${TMPDIR:-$SHARED_INSTALLER_TEMP}/post-install-launch.sh
    echo "Creating post-install launch script $launch_script..."
    cat <<EOF > $launch_script
#!/bin/bash
while pgrep -fq Installer.app; do
    sleep 1
done
open -a "${shortcut_path}"
EOF
    chmod +x $launch_script
    cat $launch_script

    nohup $launch_script &>/dev/null &
elif [[ -n "$(which gtk-launch)" ]]; then
    gtk-launch $(basename ${shortcut_path})
else
    nohup $spy_exe &>/dev/null &
fi
