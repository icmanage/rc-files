#!/usr/bin/env bash

# This will pull the infrastructure module and install it
# curl -sSL --retry 5 https://github.com/icmanage/rc-files/raw/main/bin/install_stack_builder.sh | sh -s -- -vvv

if ! [ -x "$(command -v sudo)" ]; then
    user=`whoami`
    if [ ${user}=='root' ]; then
        yum install -y sudo > /dev/null
        echo 'root ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/91-root
    else
        echo 'Error: sudo is not installed.' >&2
        exit 1
    fi
fi

# This is how pulling from a private github repo (using git+ssh) is enabled.
_MISSING_AUTH_SOCK=0
if [ -z "${SSH_AUTH_SOCK}" ] ; then
  echo ""
  echo "Error:  No SSH_AUTH_SOCK Found!!"
  _MISSING_AUTH_SOCK=1
fi

if [ $_MISSING_AUTH_SOCK = 1 ]; then
  echo ""
  echo -n "You must ensure that 'ForwardAgent'"
  echo " is set in your ~/.ssh/config.  To do that create or add to your .ssh/config the following:"
  echo ""
  echo "Host *"
  echo "  ForwardAgent yes";
  echo ""
  exit 255
fi

PYTHON_VERSION=3.8.6
PYTHON_BASE_VERSION=`echo ${PYTHON_VERSION} | cut -d "." -f 1-2`
if ! [ -x "$(command -v python${PYTHON_BASE_VERSION})" ]; then
    echo "Python ${PYTHON_VERSION} is not installed."
    sudo yum groups mark install "Development Tools"
    sudo yum -y groupinstall "Development Tools"
    sudo yum -y install openssl-libs openssl-devel bzip2-devel zlib zlib-devel libffi-devel wget git nmap-ncat which dbus-glib-devel readline-devel
    # Build up Python $PYTHON_VERSION
    cd /usr/src || echo "Unable to cd to /usr/src"
    sudo wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz
    sudo tar xzf Python-${PYTHON_VERSION}.tgz
    cd /usr/src/Python-${PYTHON_VERSION}  || echo "Unable to cd to /usr/src/Python-${PYTHON_VERSION}"
    sudo ./configure --enable-optimizations
    sudo make < /dev/null
    sudo make install < /dev/null
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
    sudo -HE pip3 install -qq --upgrade --no-cache-dir git+ssh://git@github.com/pivotal-energy-solutions/tensor-infrastructure.git || (c=$?; echo "Issue updating infrastructure"; (exit $c))
    if ! [ -f /root/.env ]; then
      sudo touch /root/.env
    fi
else
    ssh-keygen -F github.com > /dev/null 2>&1 || ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
    pip3 uninstall -qq infrastructure -y
    pip3 install -qq --upgrade --no-cache-dir git+ssh://git@github.com/icmanage/peercache-infrastructure.git || (c=$?; echo "Issue updating infrastructure"; (exit $c))
    if ! [ -f ~/.env ]; then
      touch ~/.env
    fi
fi

echo "Starting Create or Update AMI"

#create_or_update_ami.py "$@"

if [ $? -eq 0 ] ; then
    echo ""
    echo ""
    echo " Install Complete!!"
    echo ""
    echo ""
else
  echo "This FAILED!! -- NOT GOOD!"
