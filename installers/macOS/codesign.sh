#!/usr/bin/env bash
set -e

help(){ cat <<EOF
$(basename $0) [-h] FILE
Codesign an application bundle or dmg image.

Required:
  FILE        Path to the application bundle or dmg image to be signed

Options:
  -h          Display this help
  -u          Unsign code

EOF
}

while getopts ":hu" option; do
    case $option in
        (h) help; exit ;;
        (u) unsign=0 ;;
    esac
done
shift $(($OPTIND - 1))

exec 3>&1  # Additional output descriptor for logging
log(){
    level="INFO"
    date "+%Y-%m-%d %H:%M:%S [$level] [codesign] -> $1" 1>&3
}

[[ $# = 0 ]] && log "File not provided" && exit 1

# Resolve full path; works for both .app and .dmg
FILE=$(cd $(dirname $1) && pwd -P)/$(basename $1)
qt_ent_file=$(cd $(dirname $BASH_SOURCE) && pwd -P)/qt_webengine.xml

# --- Get certificate id
CNAME=$(security find-identity -p codesigning -v | pcregrep -o1 "\(([0-9A-Z]+)\)")
log "Certificate ID: $CNAME"

if [[ -n "${unsign}" ]]; then
    csopts=("--remove-signature")
else
    csopts=("--force" "--verify" "--verbose" "--timestamp" "--sign" "$CNAME")
fi

# --- Helper functions
code-sign(){
    codesign $@
#     echo $@
}

sign-dir(){
    dir=$1; shift
    for f in $(find "$dir" "$@"); do
        code-sign ${csopts[@]} $f
    done
}

if [[ "$FILE" = *".app" ]]; then
    frameworks="$FILE/Contents/Frameworks"
    resources="$FILE/Contents/Resources"
    libdir="$resources/lib"
    pydir=$(find "$libdir" -maxdepth 1 -type d -name python*)

    # --- Sign resources
    log "Signing 'so' and 'dylib' files..."
    sign-dir "$resources" \( -name *.so -or -name *.dylib \)

    # --- Sign micromamba
    log "Signing micromamba..."
    code-sign ${csopts[@]} -o runtime "$pydir/spyder/bin/micromamba"

    # --- Sign Qt frameworks
    log "Signing Qt frameworks..."
    for fwk in "$pydir"/PyQt5/Qt5/lib/*.framework; do
        if [[ "$fwk" = *"QtWebEngineCore"* ]]; then
            subapp="$fwk/Helpers/QtWebEngineProcess.app"
            code-sign ${csopts[@]} -o runtime --entitlements $qt_ent_file "$subapp"
        fi
        sign-dir "$fwk" -type f -perm +111 -not -path *QtWebEngineProcess.app*
        code-sign ${csopts[@]} "$fwk"
    done

    # --- Sign zip contents
    log "Signing 'dylib' files in zip archive..."
    pushd "$libdir"
    zipfile=python*.zip
    zipdir=$(echo $zipfile | egrep -o "python[0-9]+")
    unzip -q $zipfile -d $zipdir
    sign-dir $zipdir -name *.dylib
    ditto -c -k $zipdir $zipfile
    rm -d -r -f $zipdir
    popd

    # --- Sign app frameworks
    log "Signing app frameworks..."
    pyfwk="$frameworks/Python.framework"
    if [[ -e $pyfwk ]]; then
        # Python.framework is not present on CI
        code-sign ${csopts[@]} $pyfwk
    fi
    sign-dir "$frameworks" -name *.dylib

    # --- Sign bundle
    log "Signing app bundle..."
    code-sign ${csopts[@]} -o runtime "$FILE/Contents/MacOS/python"
    code-sign ${csopts[@]} -o runtime "$FILE/Contents/MacOS/Spyder"
fi

if [[ "$FILE" = *".dmg" ]]; then
    # --- Sign dmg
    log "Signing dmg image..."
    code-sign ${csopts[@]} "$FILE"
fi
