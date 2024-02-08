#!/usr/bin/env bash
set -e

SPYTMPDIR=${TMPDIR}spyder
CERTFILE=$SPYTMPDIR/certificate.p12
KEY_PASS=keypass
KEYCHAIN=build.keychain
KEYCHAINFILE=$HOME/Library/Keychains/$KEYCHAIN-db

help(){ cat <<EOF
$(basename $0) [-h] [-c] PASS CERT [CERT, ...]
Create build.keychain and import Developer ID certificate.
Creating a separate keychain is necessary in order to set properties of the
keychain that allow it to be accessed without GUI prompt.

Required:
  PASS        Password used to encode certificates. All certificates should
              use the same password.

  CERT        base64 encoded Developer ID certificate and private key.
              Multiple certificates may be passed as additional arguments.

Options:
  -h          Display this help

  -c          Clean up. Delete the certificate file and build.keychain

EOF
}

exec 3>&1
log(){
    level="INFO"
    date "+%Y-%m-%d %H:%M:%S [$level] [keychain] -> $1" 1>&3
}

cleanup(){
    [[ ! -e $KEYCHAINFILE ]] && return
    log "Removing $KEYCHAIN..."
    security list-keychain -s login.keychain
    security delete-keychain $KEYCHAIN
    rm -rf $CERTFILE
}

while getopts "hc" option; do
    case $option in
        (h) help; exit ;;
        (c) cleanup; exit ;;
    esac
done
shift $(($OPTIND - 1))

[[ $# < 2 ]] && log "Password and certificate(s) not provided" && exit 1
PASS=$1; shift
CERTS=($@)

# --- Create keychain
cleanup
log "Creating keychain $KEYCHAIN..."
security create-keychain -p $KEY_PASS $KEYCHAIN
security list-keychains -s $KEYCHAIN
security set-keychain-settings -lut 21600 $KEYCHAIN
security unlock-keychain -p $KEY_PASS $KEYCHAIN

log "Importing certificate(s)..."
args=("-k" "$KEYCHAIN" "-P" "$PASS" "-T" "/usr/bin/codesign" "-T" "/usr/bin/productsign")
for cert in ${CERTS[@]}; do
    if [[ -e $cert ]]; then
        log "Importing cert file $cert..."
        _cert=$cert
    else
        log "Decoding/importing base64 cert..."
        echo $cert | base64 --decode > $CERTFILE
        _cert=$CERTFILE
    fi
    security import $_cert ${args[@]}
done

# Ensure that applications can access the cert without GUI prompt
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k $KEY_PASS $KEYCHAIN

# verify import
log "Verifying identity..."
security find-identity -p codesigning -v $KEYCHAIN
