#!/usr/bin/env bash
set -e

help(){ cat <<EOF
$(basename $0) [-h] [-p] DMG
Codesign an application bundle or dmg image.

Required:
  DMG         Path to the dmg image to be notarized

Options:
  -h          Display this help

  -i INTERVAL Interval in seconds at which notarization status is polled.
              Default is 30s.

  -p PWD      Developer application-specific password

EOF
}

INTERVAL=30

while getopts "hi:p:" option; do
    case $option in
        (h) help; exit ;;
        (i) INTERVAL=$OPTARG ;;
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

APPLEID="mrclary@me.com"
BUNDLEID="com.spyder-ide.Spyder"

DMG=$(cd $(dirname $1) && pwd -P)/$(basename $1)  # Resolve full path

# --- Get certificate id
CNAME=$(security find-identity -p codesigning -v | pcregrep -o1 "\(([0-9A-Z]+)\)")
log "Certificate ID: $CNAME"

# --- Notarize
log "Notarizing..."
auth_args=("--username" "$APPLEID" "--password" "$PWD" "--asc-provider" "$CNAME")

xcrun altool --notarize-app  --file $DMG --primary-bundle-id $BUNDLEID ${auth_args[@]} | tee result.txt
requuid=$(pcregrep -o1 "^\s*RequestUUID = ([0-9a-z-]+)$" result.txt)

status="in progress"
while [[ "$status" = "in progress" ]]; do
    sleep $INTERVAL
    xcrun altool --notarization-info $requuid ${auth_args[@]} > result.txt
    status=$(pcregrep -o1 "^\s*Status: ([\w\s]+)$" result.txt)
    log "Status: $status"
done

log "Notary log:"
logurl=$(pcregrep -o1 "^\s*LogFileURL: (.*)$" result.txt)
curl $logurl

rm result.txt

if [[ $status = "success" ]]; then
    log "Stapling notary ticket..."
    xcrun stapler staple -v "$DMG"
else
    log "Notarization unsuccessful"
    exit 1
fi
