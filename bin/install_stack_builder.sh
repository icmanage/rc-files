#!/usr/bin/env bash

# This will pull the infrastructure module and install it
# curl -sSL --retry 5 https://github.com/icmanage/rc-files/raw/main/bin/install_stack_builder.sh | sh -s -- -vvv

if ! [ -x "$(command -v sudo)" ]; then
    user=`whoami`
    if [ "${user}" == "root" ]; then
        echo "Installing sudo"
        yum install -y sudo > /dev/null 2>&1
        echo 'root ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/91-root
    else
        echo 'Error: sudo is not installed.' >&2
        exit 1
    fi
fi

# This is how pulling from a private github repo (using git+ssh) is enabled.
_MISSING_AUTH_SOCK=0
if [ -z "${SSH_AUTH_SOCK}" ] ; then
  _MISSING_AUTH_SOCK=1
fi

_MISSING_SSH_PRIVATE_KEY=0
if [ -z "${SSH_PRIVATE_KEY}" ] ; then
  _MISSING_SSH_PRIVATE_KEY=1
fi

_INSTALLED_SSH_KEY=0
if [ $_MISSING_SSH_PRIVATE_KEY==1 ]; then
  if [ -e "${HOME}/.ssh/id_rsa" ]; then
    echo "Using default ~/.ssh/id_rsa key"
    _MISSING_SSH_PRIVATE_KEY=0
  fi
else
  mkdir -p ${HOME}/.ssh
  if [ ! -e "${HOME}/.ssh/id_rsa" ]; then
    echo $SSH_PRIVATE_KEY > ${HOME}/.ssh/id_rsa
    _INSTALLED_SSH_KEY=1
  else
    echo "${HOME}/.ssh/id_rsa already exists! Not going to overwrite this!!"
    _MISSING_SSH_PRIVATE_KEY=1
  fi
fi

if [ $_MISSING_AUTH_SOCK = 1 ] && [ $_MISSING_SSH_PRIVATE_KEY = 1 ]; then
  echo ""
  echo "Missing SSH KEYS"
  echo ""
  echo "We need a way to connect to github to pull the peercache-infrastructure repository"
  echo "We do this in one of two ways.  Either through the SSH_AUTH_SOCK or by passing your "
  echo "SSH Private Key to this host via variable SSH_PRIVATE_KEY"
  echo ""
  echo "If you came to this host via ssh you must ensure that you have 'ForwardAgent'"
  echo "is set in your ~/.ssh/config.  To do that create or add to your .ssh/config the following:"
  echo ""
  echo "Host *"
  echo "  ForwardAgent yes";
  echo ""
  echo "Otherwise you need to pass the environment variable SSH_PRIVATE_KEY which should contain"
  echo "your SSH private key (That gets you into github).  Something like this should work for"
  echo "docker:"
  echo " "
  echo "  docker run -e=SSH_PRIVATE_KEY=\"\$(cat ~/.ssh/id_rsa)\" --rm -it centos bash"
  echo ""
  exit 255
fi

. /etc/os-release

PYTHON_VERSION=3.8.6
PYTHON_BASE_VERSION=`echo ${PYTHON_VERSION} | cut -d "." -f 1-2`
if ! [ -x "$(command -v python${PYTHON_BASE_VERSION})" ]; then
    echo "Python ${PYTHON_VERSION} is not installed."
    sudo yum groups mark install "Development Tools"
    sudo yum -y groupinstall "Development Tools" > /dev/null 2>&1
    sudo yum -y install openssl-libs openssl-devel bzip2-devel zlib zlib-devel \
      libffi-devel wget git nmap-ncat which dbus-glib-devel readline-devel > /dev/null 2>&1
    # Build up Python $PYTHON_VERSION
    cd /usr/src || echo "Unable to cd to /usr/src"
    sudo wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz
    sudo tar xzf Python-${PYTHON_VERSION}.tgz
    cd /usr/src/Python-${PYTHON_VERSION}  || echo "Unable to cd to /usr/src/Python-${PYTHON_VERSION}"; exit 255
    OPTS="--enable-optimizations"
    if [ ${ID} == 'centos' ] || [ ${ID} == 'amzn' ] || [ ${ID} == 'rhel' ]; then
        if [ ${VERSION_ID} == "6" ] || [ ${VERSION_ID} == "7" ]; then
            OPTS=""
        fi
    fi
    sudo ./configure ${OPTS} > /dev/null 2>&1 || echo "Unable to configure"; exit 255
    sudo make < /dev/null > /dev/null 2>&1 || echo "Unable to make"; exit 255
    sudo make install < /dev/null  || echo "Unable to make install"; exit 255
    cd /usr/src || echo "Unable to cd to /usr/src"
    sudo rm -rf /usr/src/Python-${PYTHON_VERSION}
    sudo rm -f /usr/src/Python-${PYTHON_VERSION}.tgz
fi

# Build up Python PYTHON_BASE_VERSION Links so it's easy to find it
if [ ! -L /usr/bin/python${PYTHON_BASE_VERSION} ]; then
  sudo ln -s /usr/local/bin/python${PYTHON_BASE_VERSION} /usr/bin/python${PYTHON_BASE_VERSION}
  sudo ln -s /usr/local/bin/python${PYTHON_BASE_VERSION} /usr/bin/python3
  sudo ln -s /usr/local/bin/pip${PYTHON_BASE_VERSION} /usr/bin/pip${PYTHON_BASE_VERSION}
  sudo ln -s /usr/local/bin/pip3 /usr/bin/pip3
  sudo ln -s /usr/local/bin/easy_install-${PYTHON_BASE_VERSION} /usr/bin/easy_install-${PYTHON_BASE_VERSION}
  sudo ln -s /usr/local/bin/easy_install-${PYTHON_BASE_VERSION} /usr/bin/easy_install-3
fi

echo "Python ${PYTHON_VERSION} is installed."

if ! [ -x "$(command -v git)" ]; then
    echo "Git is not Installing"
    sudo yum install -y git
fi

# Update pip and install pipenv and uwsgi
sudo -HE /usr/bin/pip${PYTHON_BASE_VERSION} install -q --upgrade pip  || echo "Unable to upgrade pip"
sudo -HE /usr/bin/pip${PYTHON_BASE_VERSION} install -q --upgrade virtualenv || echo "Unable to upgrade virtualenv"
sudo -HE /usr/bin/pip${PYTHON_BASE_VERSION} install -q --upgrade poetry || echo "Unable to upgrade poetry"
sudo -HE /usr/bin/pip${PYTHON_BASE_VERSION} install -q --upgrade uwsgi || echo "Unable to upgrade uwsgi"
sudo -HE /usr/bin/pip${PYTHON_BASE_VERSION} install -q --upgrade dbus-python || echo "Unable to upgrade dbus-python"

# Ensure we are good with github
if ! [ $(id -u) = 0 ]; then
    sudo -HE ssh-keygen -F github.com > /dev/null 2>&1 || \
      ssh-keyscan github.com 2> /dev/null | sudo tee -a /root/.ssh/known_hosts > /dev/null && \
      sudo chown root:root /root/.ssh/known_hosts && \
      sudo chmod 640 /root/.ssh/known_hosts
    sudo -HE pip3 uninstall -qq infrastructure -y
    sudo -HE pip3 install -qq --upgrade --no-cache-dir git+ssh://git@github.com/icmanage/peercache-infrastructure.git || (c=$?; echo "Issue updating infrastructure"; (exit $c))
else
    ssh-keygen -F github.com > /dev/null 2>&1 || ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
    pip3 uninstall -qq infrastructure -y
    pip3 install -qq --upgrade --no-cache-dir git+ssh://git@github.com/icmanage/peercache-infrastructure.git || (c=$?; echo "Issue updating infrastructure"; (exit $c))
fi

echo "All done"

#create_or_update_ami.py "$@"

if [ $_INSTALLED_SSH_KEY = 1 ]; then
  rm "${HOME}/.ssh/id_rsa"
fi


if [ $? -eq 0 ] ; then
    echo ""
    echo ""
    echo " Install Complete!!"
    echo ""
    echo ""
else
  echo "This FAILED!! -- NOT GOOD!"
fi