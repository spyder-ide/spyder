#!/usr/bin/env bash
set -e

help(){ cat <<EOF
$(basename $0) [-h] [-p] DMG
Codesign an application bundle or dmg image.

Required:
  DMG         Path to the dmg image to be notarized

Options:
  -h          Display this help

  -p PWD      Developer application-specific password

EOF
}

while getopts "hp:" option; do
    case $option in
        (h) help; exit ;;
        (p) PWD=$OPTARG ;;
    esac
done
shift $(($OPTIND - 1))

exec 3>&1  # Additional output descriptor for logging
log(){
    level="INFO"
    date "+%Y-%m-%d %H:%M:%S [$level] [notarize] -> $1" 1>&3
}

[[ -z $PWD ]] && log "Application-specific password not provided" && exit 1
[[ $# = 0 ]] && log "File not provided" && exit 1

DMG=$(cd $(dirname $1) && pwd -P)/$(basename $1)  # Resolve full path

# --- Get certificate id
CNAME=$(security find-identity -p codesigning -v | pcregrep -o1 "\(([0-9A-Z]+)\)")
log "Certificate ID: $CNAME"

# --- Notarize
log "Notarizing..."
xcrun notarytool submit $DMG --wait --team-id $CNAME --apple-id mrclary@me.com --password "$PWD" | tee temp.txt

submitid=$(pcregrep -o1 "^\s*id: ([0-9a-z-]+)" temp.txt | head -1)
status=$(pcregrep -o1 "^\s*status: (\w+$)" temp.txt)
rm temp.txt

log "Notary log:"
xcrun notarytool log $submitid --team-id $CNAME --apple-id mrclary@me.com --password "$PWD"

if [[ "$status" = "Accepted" ]]; then
    log "Stapling notary ticket..."
    xcrun stapler staple -v "$DMG"
fi

# spctl -a -t exec -vv $DMG
