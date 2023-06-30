#!/bin/bash -i
set -e

echo "*** Running post install script for ${INSTALLER_NAME} ..."

echo "Args = $@"
echo "Environment variables:"
env | sort
echo ""

# ----
name_lower=$(echo ${INSTALLER_NAME} | tr 'A-Z' 'a-z')
spy_exe=${PREFIX}/envs/spyder-runtime/bin/spyder
u_spy_exe=${PREFIX}/uninstall-spyder.sh

sed_opts=("-i")
alias_text="alias uninstall-spyder=${u_spy_exe}"
if [[ $OSTYPE = "darwin"* ]]; then
    shortcut_path="/Applications/Spyder.app"
    [[ ${PREFIX} = "$HOME"* ]] && shortcut_path="${HOME}${shortcut_path}"
    sed_opts+=("", "-e")
else
    shortcut_path="$HOME/.local/share/applications/${name_lower}_${name_lower}.desktop"
    alias_text="alias spyder=${spy_exe}\n${alias_text}"
fi

case $SHELL in
    (*"zsh") shell_init=$HOME/.zshrc ;;
    (*"bash") shell_init=$HOME/.bashrc ;;
esac

m1="# >>> Added by Spyder >>>"
m2="# <<< Added by Spyder <<<"

add_alias() (
    if [[ ! -f "$shell_init" || ! -s "$shell_init" ]]; then
        echo -e "$m1\n$1\n$m2" > $shell_init
        exit 0
    fi

    # Remove old-style markers, if present; discard after EXPERIMENTAL
    # installer attrition.
    sed ${sed_opts[@]} "/# <<<< Added by Spyder <<<</,/# >>>> Added by Spyder >>>>/d" $shell_init

    # Posix compliant sed does not like semicolons.
    # Must use newlines to work on macOS
    sed ${sed_opts[@]} "
    /$m1/,/$m2/{
        h
        /$m2/ s|.*|$m1\n$1\n$m2|
        t
        d
    }
    \${
        x
        /^$/{
            s||\n$m1\n$1\n$m2|
            H
        }
        x
    }" $shell_init
)

# ----
echo "Creating uninstall script..."
cat <<END > ${u_spy_exe}
#!/bin/bash

while getopts "f" option; do
    case "\$option" in
        (f) force=true ;;
    esac
done
shift \$((\$OPTIND - 1))

if [[ -z \$force ]]; then
    cat <<EOF
You are about to uninstall Spyder.
If you proceed, aliases will be removed from ${shell_init}
(if present) and the following will be removed:
  ${shortcut_path}
  ${PREFIX}

Do you wish to continue?
EOF
    read -p " [yes|NO]: " confirm
    if [[ \$confirm != [yY] && \$confirm != [yY][eE][sS] ]]; then
        echo "Uninstall aborted."
        exit 1
    fi
fi

if [[ \$OSTYPE = "darwin"* ]]; then
    echo "Quitting Spyder.app..."
    osascript -e 'quit app "Spyder.app"' 2> /dev/null
fi

# Remove aliases from shell startup
if [[ -f "$shell_init" ]]; then
    echo "Removing shell commands..."
    sed ${sed_opts[@]} "/$m1/,/$m2/d" $shell_init
fi

# Remove shortcut and environment
echo "Removing Spyder and environment..."
rm -rf ${shortcut_path}
rm -rf ${PREFIX}

echo "Spyder successfully uninstalled."
END
chmod u+x ${u_spy_exe}

# ----
if [[ -n "$shell_init" ]]; then
    echo "Creating aliases in $shell_init ..."
    add_alias "$alias_text"
fi

# ----
if [[ $OSTYPE = "linux"* ]]; then
    cat <<EOF

###############################################################################
#                             !!! IMPORTANT !!!
###############################################################################
Spyder can be launched by standard methods in Gnome and KDE desktop
environments. It can also be launched from the command line on all Linux
distros with the command:

$ spyder

To uninstall Spyder, run the following from the command line:

$ uninstall-spyder

These commands will only be available in new shell sessions. To make them
available in this session, you must source your $shell_init file with:

$ source $shell_init

###############################################################################

EOF
fi

echo "*** Post install script for ${INSTALLER_NAME} complete"

# ----
[[ -n "$CI" ]] && exit 0  # Running in CI, don't launch Spyder
if [[ "$OSTYPE" = "darwin"* ]]; then
    open -a $shortcut_path
elif [[ "$XDG_CURRENT_DESKTOP" =~ .*(Unity|GNOME|XFCE).* ]]; then
    gtk-launch spyder_spyder
fi
