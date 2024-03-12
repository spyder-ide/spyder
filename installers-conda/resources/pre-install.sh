#!/bin/bash
set -e
echo "*** Running pre install script for ${INSTALLER_NAME} ..."

echo "Marking as conda-based-app..."
menudir="${PREFIX}/envs/spyder-runtime/Menu"
mkdir -p "$menudir"
touch "${menudir}/conda-based-app"

echo "*** Pre install script for ${INSTALLER_NAME} complete"
