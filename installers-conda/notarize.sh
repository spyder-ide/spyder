#!/usr/bin/env bash

help(){ cat <<EOF
$(basename $0) [-h] [-t TIMEOUT] [-v] [-p PASSWORD] PKG
Notarize and staple an installer package.

Required:
  PKG         Path to the PKG file to be notarized

Options:
  -h          Display this help

  -t TIMEOUT  Timeout for notarization, e.g. 30m

  -p PASSWORD Developer application-specific password. If not provided, will
              attempt using credentials saved under spyder-ide keychain
              profile.

  -v          Verbose

EOF
}

exec 3>&1  # Additional output descriptor for logging
log(){
    level="INFO"
    date "+%Y-%m-%d %H:%M:%S [$level] [notarize] -> $1" 1>&3
}

notarize_args=("--apple-id" "mrclary@me.com")
pwd_args=("-p" "spyder-ide")
while getopts "ht:p:v" option; do
    case $option in
        (h) help; exit ;;
        (t) notarize_args+=("--timeout" "$OPTARG") ;;
        (p) pwd_args=("--password" "$OPTARG") ;;
        (v) notarize_args+=("--verbose") ;;
    esac
done
shift $(($OPTIND - 1))

[[ $# = 0 ]] && log "File not provided" && exit 1

PKG=$(cd $(dirname $1) && pwd -P)/$(basename $1)  # Resolve full path

# --- Get certificate id
CNAME=$(security find-identity -p codesigning -v | pcregrep -o1 "\(([0-9A-Z]+)\)")
[[ -z $CNAME ]] && log "Could not locate certificate ID" && exit 1
log "Certificate ID: $CNAME"

notarize_args+=("--team-id" "$CNAME" "${pwd_args[@]}")

# --- Notarize
log "Notarizing..."
xcrun notarytool submit $PKG --wait ${notarize_args[@]} | tee temp.txt

submitid=$(pcregrep -o1 "^\s*id: ([0-9a-z-]+)" temp.txt | head -1)
status=$(pcregrep -o1 "^\s*status: (\w+$)" temp.txt)
rm temp.txt

xcrun notarytool log $submitid ${notarize_args[@]}

if [[ "$status" != "Accepted" ]]; then
    log "Notarizing failed!"
    exit 1
fi

log "Stapling notary ticket..."
xcrun stapler staple -v "$PKG"
if [[ $? != 0 ]]; then
    log "Stapling failed!"
    exit 1
fi
