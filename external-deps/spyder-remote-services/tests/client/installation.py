MICROMAMBA_INSTALLER = """\
"${SHELL}" <(curl -L micro.mamba.pm/install.sh)
"""

MICROMAMBA_INSTALLER_PS = """\
Invoke-Expression ((Invoke-WebRequest -Uri https://micro.mamba.pm/install.ps1).Content)
"""
