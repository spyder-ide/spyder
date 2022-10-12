#!/bin/bash

timeout=90
interval=1
delay=10

help() { cat <<EOF

$(basename $0) [-t timeout] [-i interval] [-d delay] distdir
Launch Spyder.app located in distdir with a time-out.
Upon time-out expiration SIGTERM (15) is sent to Spyder. If SIGTERM
signal is blocked, then the subsequent SIGKILL (9) terminates it.

  distdir     Directory in which Spyder.app resides.

  -t timeout  Number of seconds to wait for command completion.
              Default value: $timeout seconds.

  -i interval Interval between checks if the process is still alive.
              Positive integer, default value: $interval seconds.

  -d delay    Delay between posting the SIGTERM signal and destroying the
              process by SIGKILL. Default value: $delay seconds.

Bash does not support floating point arithmetic (sleep does),
therefore all delay/time values must be integers.

EOF
}

# Options.
while getopts ":t:i:d:" option; do
    case "$option" in
        t) timeout=$OPTARG ;;
        i) interval=$OPTARG ;;
        d) delay=$OPTARG ;;
        *) help; exit 0 ;;
    esac
done
shift $(($OPTIND - 1))

distdir=$1
if [[ -z $distdir ]]; then
    help && exit 1
fi

export SPYDER_DEBUG=3
export INSTALLER_TEST=1
$1/Spyder.app/Contents/MacOS/Spyder &
pid=$!

t=$timeout
while [[ $t > 0 ]]; do
    sleep $interval
    if ! $(kill -0 $pid 2> /dev/null); then
        echo -e "\nSpyder shut down after $((timeout - t))s" && exit 1
    fi
    ((t -= $interval))
done
echo -e "\nSpyder launched successfully!"

echo -e "Shutting down Spyder...\n"
kill -s SIGTERM $pid 2> /dev/null

t=$delay
while [[ $t > 0 ]]; do
    sleep $interval
    if ! $(kill -0 $pid 2> /dev/null); then
        echo -e "\nSpyder shut down successfully in $((delay - t))s" && exit 0
    fi
    ((t -= $interval))
done

echo -e "\nSpyder did not shut down properly; killing..."
kill -s SIGKILL $pid && exit 1
