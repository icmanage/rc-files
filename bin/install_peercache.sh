#!/usr/bin/env bash

# This will pull the infrastructure module and install it
# Alternatively this can be bundled so we can decouple the entire thing to a private cloud.

# curl -sSL --retry 5 https://github.com/icm_manage/rc-files/raw/master/bin/install_peercache.sh | sh -s -- -c tracker -vvv

if ! [ -x "$(command -v sudo)" ]; then
    echo 'Error: sudo is not installed.' >&2
    exit 1
fi

# We need to make sure that we allow these couple keys to be passed to our host.
_SSHD_INCORRECT=0
sudo grep -P '^AcceptEnv\s+(?=.*AWS_ACCESS_KEY_ID)(?=.*AWS_SECRET_ACCESS_KEY)(?=.*EC2_REGION)' /etc/ssh/sshd_config > /dev/null
if [ $? != 0 ] ; then
  _SSHD_INCORRECT=1
  echo ""
  echo "Warning: SSHD is not accepting of SendEnv Keys - Fixing"
  echo "         This is needed to ensure we can orchestrate the build across all hosts"
  echo "" | sudo tee -a /etc/ssh/sshd_config > /dev/null
  echo "AcceptEnv AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY EC2_REGION" | sudo tee -a /etc/ssh/sshd_config > /dev/null
  sudo systemctl restart sshd
  echo "  Corrected.  A re-login will be required"
fi

echo "Good we are starting"