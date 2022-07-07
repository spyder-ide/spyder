#!/usr/bin/env bash
set -e

CERTFILE=certificate.p12
KEY_PASS=keypass
KEYCHAIN=build.keychain
KEYCHAINFILE=$HOME/Library/Keychains/$KEYCHAIN-db

help(){ cat <<EOF
$(basename $0) [-h] [-c] CERT PASS
Create build.keychain and import Developer ID certificate.
Creating a separate keychain is necessary in order to set properties of the
keychain that allow it to be accessed without GUI prompt.

Required:
  CERT        base64 encoded Developer ID certificate and private key
  PASS        Password used to encode CERT

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

while getopts "hc" option; do
    case $option in
        (h) help; exit ;;
        (c) cleanup; exit ;;
    esac
done
shift $(($OPTIND - 1))

[[ $# < 2 ]] && log "Certificate and/or certificate password not provided" && exit 1

CERT=$1
PASS=$2

# --- Prepare the certificate
# decode certificate-as-Github-secret back to p12 for import into keychain
log "Decoding Certificate..."
echo $CERT | base64 --decode > $CERTFILE

# --- Create keychain
log "Creating keychain..."
security create-keychain -p $KEY_PASS $KEYCHAIN

# Set keychain to default and unlock it so that we can add the certificate
# without GUI prompt
log "Importing certificate..."
security default-keychain -s $KEYCHAIN
security unlock-keychain -p $KEY_PASS $KEYCHAIN
security import $CERTFILE -k $KEYCHAIN -P $PASS -T /usr/bin/codesign

# Ensure that codesign can access the cert without GUI prompt
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k $KEY_PASS $KEYCHAIN

# verify import
log "Verifying identity..."
security find-identity -p codesigning -v $KEYCHAIN
