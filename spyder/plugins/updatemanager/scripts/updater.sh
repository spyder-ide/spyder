#!/bin/bash
set -e  # Exit if there is an error

conda_exe="$1"  # conda executable path
conda_cmd="$2"  # conda subcommand
env_path="$3"   # Environment path
spy_updater_lock="$4"  # Environment lock file
spy_updater_conda="$5"  # Updater conda package

tmp_update_dir="$(dirname $spy_updater_lock)"

set -x
"$conda_exe" $conda_cmd -q --yes --prefix "$env_path" --file "$spy_updater_lock"
"$conda_exe" install -q --yes --prefix "$env_path" --no-deps --force-reinstall "$spy_udater_conda"
