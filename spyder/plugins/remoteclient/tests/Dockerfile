FROM ubuntu:focal AS ubuntu-base
ENV DEBIAN_FRONTEND noninteractive
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Setup the default user.
RUN useradd -rm -d /home/ubuntu -s /bin/bash -g root -G sudo ubuntu
RUN echo 'ubuntu:ubuntu' | chpasswd

# Install required tools.
RUN apt-get -qq update \
    && apt-get -qq --no-install-recommends install curl \
    && apt-get -qq --no-install-recommends install ca-certificates \
    && apt-get -qq --no-install-recommends install vim-tiny \
    && apt-get -qq --no-install-recommends install sudo \
    && apt-get -qq --no-install-recommends install openssh-server \
    && apt-get -qq clean \
    && rm -rf /var/lib/apt/lists/*

# Configure SSHD.
# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
RUN mkdir /var/run/sshd
RUN bash -c 'install -m755 <(printf "#!/bin/sh\nexit 0") /usr/sbin/policy-rc.d'
RUN ex +'%s/^#\zeListenAddress/\1/g' -scwq /etc/ssh/sshd_config
RUN ex +'%s/^#\zeHostKey .*ssh_host_.*_key/\1/g' -scwq /etc/ssh/sshd_config
RUN RUNLEVEL=1 dpkg-reconfigure openssh-server
RUN ssh-keygen -A -v
RUN update-rc.d ssh defaults

# Configure sudo.
RUN ex +"%s/^%sudo.*$/%sudo ALL=(ALL:ALL) NOPASSWD:ALL/g" -scwq! /etc/sudoers

# Generate and configure user keys.
USER ubuntu
RUN ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519

CMD ["/usr/bin/sudo", "/usr/sbin/sshd", "-D", "-o", "ListenAddress=172.16.128.2"]
