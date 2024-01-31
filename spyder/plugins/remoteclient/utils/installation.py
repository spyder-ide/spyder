ENVIROMENT_NAME = "spyder-remote"
PACKAGE_NAME = "spyder-remote-server"

MICROMAMBA_INSTALLER_SH = f"""
#!/bin/bash

# Download and install Micromamba
{{SHELL}} <(curl -L micro.mamba.pm/install.sh) && \\

# Initialize Micromamba shell integration
eval "$(~/micromamba shell hook --shell=bash)" && \\

# Create a new environment with Python
micromamba create -y -n {ENVIROMENT_NAME} python pip -c conda-forge && \\

# Activate the environment
micromamba activate {ENVIROMENT_NAME} && \\

# Install the spyder-remote-server package
#pip install {PACKAGE_NAME}
cd ~ && \\
git clone https://github.com/spyder-ide/spyder-remote-server
cd spyder-remote-server && \\
pip install -e . && \\

# Deactivate the environment
micromamba deactivate
"""

MICROMAMBA_INSTALLER_PS = f"""\
# Download and install Micromamba
Invoke-Expression ((Invoke-WebRequest -Uri 'https://micro.mamba.pm/install.ps1').Content)

# Initialize Micromamba shell integration (assuming Micromamba is installed in the user's home directory)
$micromambaPath = '$env:USERPROFILE\micromamba'
Invoke-Expression (& '$micromambaPath\Scripts\micromamba' shell hook --shell=powershell | Out-String)

# Create a new environment with Python and pip
& '$micromambaPath\Scripts\micromamba' create -y -n {ENVIROMENT_NAME} python pip -c conda-forge

# Activate the environment
& '$micromambaPath\Scripts\micromamba' activate {ENVIROMENT_NAME}

# Install the spyder-remote-server package
# pip install {PACKAGE_NAME}
cd $env:USERPROFILE
git clone https://github.com/spyder-ide/spyder-remote-server
cd spyder-remote-server
pip install -e .

# Deactivate the environment (Micromamba might not need explicit deactivation in PowerShell, but it's here for completeness)
& '$micromambaPath\Scripts\micromamba' deactivate
"""
