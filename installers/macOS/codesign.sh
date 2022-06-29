#!/bin/bash
set -e

CERTFILE=certificate.p12
KEY_PASS=keypass
KEYCHAIN=build.keychain
KEYCHAINFILE=$HOME/Library/Keychains/$KEYCHAIN-db

# certificate common name
CNAME="Developer ID Application: Ryan Clary (6D7ZTH6B38)"

help(){ cat <<EOF
$(basename $0) [-h] [-d] -c CERT -p PASS APP
Codesign an application.

Required:
  -c CERT     base64 encoded certificate and private key
  -p PASS     Password used to encode CERT
  APP         Path to the application bundle to be signed

Options:
  -h          Display this help
  -d          Use codesign '--deep' flag. Mutually exclusive with -e.
  -e          codesign the necessary elements beginning with the frameworks,
              then the python binary, and finally the app bundle. Mutually
              exclusive with -d.

EOF
}

cleanup () {
    security default-keychain -s login.keychain  # restore default keychain
    rm -f $CERTFILE  # remove cert file

    # remove temporary keychain
    if security delete-keychain $KEYCHAIN 2> /dev/null; then
        echo "clean up: $KEYCHAIN deleted."
    fi

    # make sure temporary keychain file is gone
    if [[ -e $KEYCHAINFILE ]]; then
        rm -f $KEYCHAINFILE
        echo "clean up: $KEYCHAINFILE file deleted"
    fi
}

unset CERT PASS DEEP ELEM APP

while getopts "hc:p:de" option; do
    case $option in
        h)
            help
            exit;;
        c)
            CERT="$OPTARG";;
        p)
            PASS="$OPTARG";;
        d)
            DEEP="--deep"
            unset ELEM;;
        e)
            ELEM=1
            unset DEEP;;
    esac
done
shift $(($OPTIND - 1))

test -z "$CERT" && error "Error: Certificate must be provided. $CERT"

test -z "$PASS" && error "Error: Password must be provided. $PASS"

test -n "$1" && APP="$1" || error "Error: Application must be provided."

# always cleanup if there is an error
trap cleanup EXIT

cleanup  # make sure keychain and file don't exist

# --- Prepare the certificate
# decode certificate-as-Github-secret back to p12 for import into keychain
echo "Decoding Certificate..."
echo $CERT | base64 --decode > $CERTFILE

# --- Create keychain
echo "Creating keychain..."
security create-keychain -p $KEY_PASS $KEYCHAIN

# Set keychain to default and unlock it so that we can add the certificate
# without GUI prompt
echo "Importing certificate..."
security default-keychain -s $KEYCHAIN
security unlock-keychain -p $KEY_PASS $KEYCHAIN
security import $CERTFILE -k $KEYCHAIN -P $PASS -T /usr/bin/codesign

# Ensure that codesign can access the cert without GUI prompt
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k $KEY_PASS $KEYCHAIN

# verify import
echo "Verifying identity..."
security find-identity -p codesigning -v $KEYCHAIN

# ---- Sign app
if [[ -n $ELEM ]]; then
    echo "Signing individual elements..."
    # sign frameworks first
    for framework in $APP/Contents/Frameworks/*; do
        codesign -f -v -s "$CNAME" "$framework"
    done

    # sign extra binary next
    echo "Signing extra binary..."
    codesign -f -v -s "$CNAME" "$APP/Contents/MacOS/python"
fi

# sign app bundle
echo "Signing application..."
codesign -f -v $DEEP -s "$CNAME" "$APP"
