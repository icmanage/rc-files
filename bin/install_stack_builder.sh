#!/usr/bin/env bash

# This will pull the infrastructure module and install it
# curl -sSL --retry 5 https://github.com/icmanage/rc-files/raw/main/bin/install_stack_builder.sh | sh -s -- -vvv

if ! [ -x "$(command -v sudo)" ]; then
  user=$(whoami)
  if [ "${user}" == "root" ]; then
    echo "Installing sudo"
    yum install -y sudo >/dev/null 2>&1
    echo 'root ALL=(ALL) NOPASSWD:ALL' >/etc/sudoers.d/91-root
  else
    echo 'Error: sudo is not installed.' >&2
    exit 1
  fi
fi

. /etc/os-release

PYTHON_VERSION=3.8.6
PYTHON_BASE_VERSION=$(echo ${PYTHON_VERSION} | cut -d "." -f 1-2)
if ! [ -x "$(command -v python${PYTHON_BASE_VERSION})" ]; then
  echo "Python ${PYTHON_VERSION} is not installed."
  sudo yum groups mark install "Development Tools"
  sudo yum -y groupinstall "Development Tools" >/dev/null 2>&1
  sudo yum -y install openssl-libs openssl-devel bzip2-devel zlib zlib-devel \
    libffi-devel wget git nmap-ncat which dbus-glib-devel readline-devel >/dev/null 2>&1
  # Build up Python $PYTHON_VERSION
  cd /usr/src || echo "Unable to cd to /usr/src"
  sudo wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz
  sudo tar xzf Python-${PYTHON_VERSION}.tgz
  cd /usr/src/Python-${PYTHON_VERSION} || echo "Unable to cd to /usr/src/Python-${PYTHON_VERSION}"
  OPTS="--enable-optimizations"
  if [ ${ID} == 'centos' ] || [ ${ID} == 'amzn' ] || [ ${ID} == 'rhel' ]; then
    if [ ${VERSION_ID} == "6" ] || [ ${VERSION_ID} == "7" ]; then
      OPTS=""
    fi
  fi
  echo "Running ./configure ${OPTS}"
  sudo ./configure ${OPTS} || echo "Unable to configure ${OPTS}"
  echo "Running make"
  sudo make </dev/null || echo "Unable to make"
  echo "Running make install"
  sudo make install </dev/null || echo "Unable to make install"
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
sudo -HE /usr/bin/pip${PYTHON_BASE_VERSION} install -q --upgrade pip || echo "Unable to upgrade pip"
sudo -HE /usr/bin/pip${PYTHON_BASE_VERSION} install -q --upgrade virtualenv || echo "Unable to upgrade virtualenv"
sudo -HE /usr/bin/pip${PYTHON_BASE_VERSION} install -q --upgrade poetry || echo "Unable to upgrade poetry"

sudo wget https://download.icmanage.com/peercache-infrastructure-current.tar.gz

# Ensure we are good with github
sudo pip3 uninstall -qq infrastructure -y
sudo pip3 install -qq --upgrade peercache-infrastructure-current.tar.gz
sudo rm peercache-infrastructure-current.tar.gz

if [ $_INSTALLED_SSH_KEY = 1 ]; then
  rm "${HOME}/.ssh/id_rsa"
fi

echo "All done"

if [ $? -eq 0 ]; then
  echo ""
  echo ""
  echo " Install Complete!!"
  echo ""
  echo ""
else
  echo "This FAILED!! -- NOT GOOD!"
fi
