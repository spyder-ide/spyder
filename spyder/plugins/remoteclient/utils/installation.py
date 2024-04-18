# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import base64


ENVIROMENT_NAME = "spyder-remote"
PACKAGE_NAME = "spyder-remote-server"
MICROMAMBA_VERSION = "latest"

MICROMAMBA_INSTALLER_SH = f"""
#!/bin/bash

VERSION="{MICROMAMBA_VERSION}"
BIN_FOLDER="${{HOME}}/.local/bin"
PREFIX_LOCATION="${{HOME}}/micromamba"

# Computing artifact location
case "$(uname)" in
  Linux)
    PLATFORM="linux" ;;
  Darwin)
    PLATFORM="osx" ;;
  *NT*)
    PLATFORM="win" ;;
esac

ARCH="$(uname -m)"
case "$ARCH" in
  aarch64|ppc64le|arm64)
      ;;  # pass
  *)
    ARCH="64" ;;
esac

case "$PLATFORM-$ARCH" in
  linux-aarch64|linux-ppc64le|linux-64|osx-arm64|osx-64|win-64)
      ;;  # pass
  *)
    echo "Failed to detect your OS" >&2
    exit 1
    ;;
esac

RELEASE_URL="https://github.com/mamba-org/micromamba-releases/releases/${{VERSION}}/download/micromamba-${{PLATFORM}}-${{ARCH}}"

# Downloading artifact
mkdir -p "${{BIN_FOLDER}}"
if hash curl >/dev/null 2>&1; then
  curl "${{RELEASE_URL}}" -o "${{BIN_FOLDER}}/micromamba" -fsSL --compressed ${{CURL_OPTS:-}}
elif hash wget >/dev/null 2>&1; then
  wget ${{WGET_OPTS:-}} -qO "${{BIN_FOLDER}}/micromamba" "${{RELEASE_URL}}"
else
  echo "Neither curl nor wget was found" >&2
  exit 1
fi
chmod +x "${{BIN_FOLDER}}/micromamba"

# Activate micromamba shell hook
eval "$("${{BIN_FOLDER}}/micromamba" shell hook --shell bash)"

git clone https://github.com/spyder-ide/spyder-remote-server
cd spyder-remote-server

micromamba create -y -n {ENVIROMENT_NAME} -f environment.yml

# Activate the environment
micromamba activate {ENVIROMENT_NAME}

# Install the spyder-remote-server package
#pip install {PACKAGE_NAME}
poetry install

"""


MICROMAMBA_INSTALLER_PS = f"""
# check if VERSION env variable is set, otherwise use "latest"
$VERSION = "{MICROMAMBA_VERSION}"

$RELEASE_URL="https://github.com/mamba-org/micromamba-releases/releases/$VERSION/download/micromamba-win-64"

Write-Output "Downloading micromamba from $RELEASE_URL"
curl.exe -L -o micromamba.exe $RELEASE_URL

New-Item -ItemType Directory -Force -Path  $Env:LocalAppData\micromamba | out-null

$MAMBA_INSTALL_PATH = Join-Path -Path $Env:LocalAppData -ChildPAth micromamba\micromamba.exe

Write-Output "`nInstalling micromamba to $Env:LocalAppData\micromamba`n"
Move-Item -Force micromamba.exe $MAMBA_INSTALL_PATH | out-null

# Add micromamba to PATH if the folder is not already in the PATH variable
$PATH = [Environment]::GetEnvironmentVariable("Path", "User")
if ($PATH -notlike "*$Env:LocalAppData\micromamba*") {{
    Write-Output "Adding $MAMBA_INSTALL_PATH to PATH`n"
    [Environment]::SetEnvironmentVariable("Path", "$Env:LocalAppData\micromamba;" + [Environment]::GetEnvironmentVariable("Path", "User"), "User")
}} else {{
    Write-Output "$MAMBA_INSTALL_PATH is already in PATH`n"
}}"""


def get_installer_command(platform: str) -> str:
    if platform == "win":
        script = MICROMAMBA_INSTALLER_PS
        encoding = "utf-16le"
        command = "powershell.exe -EncodedCommand {}"
    else:
        script = MICROMAMBA_INSTALLER_SH
        encoding = "utf-8"
        command = "echo {} | base64 --decode | /bin/bash"

    return command.format(
        base64.b64encode(script.encode(encoding)).decode(encoding)
    )


def get_enviroment_command(platform: str) -> str:
    if platform == "win":
        return f"micromamba activate {ENVIROMENT_NAME}"
    else:
        return f"source micromamba activate {ENVIROMENT_NAME}"
