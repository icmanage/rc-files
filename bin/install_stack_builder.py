#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""install stack_builder.py

This will install the stack builder.  This tool is used to dynamically build and create
holodeck stacks.

We don't need python 3 for this portion but we want to have it for the actual peercache
infrastructure package


curl -sSL https://github.com/icmanage/rc-files/raw/main/bin/install_stack_builder.py | python - -vv

"""
import argparse
import datetime
import logging
import os
import re
import subprocess
import sys
import time


def color(msg, color='default', bold=False):
    """Color some text"""
    color_dict = {'default': 0, 'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
                  'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37, }
    if not color_dict.get(color):
        logging.warning('Unknown color "{}"'.format(color))
    if '{}'.format(os.environ.get('NO_COLOR')) == '1':
        return msg
    return '\033[{};{}m{}\033[0m'.format(int(bold), color_dict.get(color, 0), msg)


def read_config(config_file, separator=' ', log=None, report=True):
    results = {}
    with open(config_file) as file_obj:
        data = file_obj.readlines()
    for line in data:
        line = line.strip()
        line
        if not len(line) or re.search(r'\s*#', line):
            continue
        line = re.sub(r'\s+', ' ', line)
        if '`hostname -i`' in line:
            line = re.sub('`hostname -i`', subprocess.check_output(['hostname', '-i']), line)
        _x = line.split(separator)
        if len(_x) != 2:
            if report:
                if log:
                    log.warning(color("Skipping %r in %r" % (line, config_file), 'yellow'))
                else:
                    print("Skipping %r in %r" % (line, config_file))
            continue
        key, value = _x
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        results[key] = value
    return results


def check_os_type(_args, log=None, **_kwargs):
    """Verify our version"""
    os_data = read_config('/etc/os-release', separator='=', log=log)
    if os_data.get('ID') == 'amzn':
        if os_data['VERSION'] != "2":
            return False, 'Amazon version %s unsupported' % os_data['VERSION']
        return True, 'Amazon version %s supported' % os_data['VERSION']
    elif os_data.get('ID') == 'rhel':
        if os_data['VERSION'] not in ["6", "7"]:
            return False, 'Redhat version %s unsupported' % os_data['VERSION']
        return True, 'Redhat version %s supported' % os_data['VERSION']
    return False, "Unable to identify ID and or VERSION from /etc/os-release"


def check_sudo_available(*_args, **_kwargs):
    """Verify sudo availability"""
    return_code = subprocess.call(['which', 'sudo'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if return_code == 0:
        return True, "Passing sudo availability.  Sudo is available"
    return False, "Failing sudo availability.  Install sudo."


def check_sudo_access(*_args, **_kwargs):
    """Verify sudo access"""
    # On aws - sudo -nv returns 0 and has ALL and NOPASSWD in the response if you can
    command = ['sudo', '-nl']
    return_code = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if return_code == 1:
        return False, "Failing sudo access - You don't appear to have sudo access"

    output = subprocess.check_output(command)
    if 'ALL' in output and 'NOPASSWD: ALL' in output:
        return True, "Passing sudo access.  User has passwordless sudo access"
    return False, "Failing passwordless sudo access.  You need to ensure you have passwordless sudo"


def check_git_available(*_args, **_kwargs):
    """Verify git availability"""
    return_code = subprocess.call(['which', 'git'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if return_code == 0:
        return True, "Passing git availability.  git is available"
    return False, "Failing git availability.  Install git."


def check_python3(*_args, **_kwargs):
    """Verify sudo availability"""
    return_code = subprocess.call(['which', 'python3'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if return_code == 0:
        return True, "Passing python 3 availability.  python3 is available"
    return False, "Failing pythond availability.  Install python 3."

def install_python3(log, version='3.8.6'):

    """
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



    :param version:
    :return:
    """
    cmds = [
        ['sudo', 'yum', 'groups', 'mark', 'install', 'Development Tools'],
        ['sudo', 'yum', '-y', 'groupinstall', 'Development Tools'],
        ['sudo', 'yum', '-y', 'install',  'openssl-libs', 'openssl-devel', 'bzip2-devel', 'zlib',
         'wget', 'zlib-devel', 'libffi-devel', 'dbus-glib-devel', 'readline-devel'],
        ['sudo', 'wget', 'https://www.python.org/ftp/python/%s/Python-%s.tgz' % (version, version)],
        ['sudo', 'tar', 'xzf', 'Python-%s.tgz' % version],

    ]
    pre_install = True
    for cmd in cmds:
        log.debug(" ".join(cmd))
        return_code = subprocess.call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if return_code != 0:
            log.error(color("Unable to run %r" % ' '.join(cmd), 'red'))
            pre_install = False
            break

    if not pre_install:
        log.error(color("Unable to pre-install python", 'red'))
        return

    os.chdir('Python-%s' % version)
    cmds = [
        ['sudo', './configure', '--enable-optimizations'],
        ['sudo', 'make'],
        ['sudo', 'make', 'install'],
    ]
    install = True
    for cmd in cmds:
        log.debug(" ".join(cmd))
        return_code = subprocess.call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if return_code != 0:
            log.error(color("Unable to run %r" % ' '.join(cmd), 'red'))
            install = False
            break
    if not install:
        log.error(color("Unable to install python", 'red'))
        return

    os.chdir('../')
    cmds = [
        ['sudo', 'rm', '-rf', 'Python-%s' % version],
        ['sudo', 'rm', 'f', 'Python-%s.tgz' % version],
    ]

    paths = [
        '/usr/bin/python%s' % version, '/usr/bin/python3'
        '/usr/bin/pip%s' % version, '/usr/bin/pip3'
        '/usr/bin/easy_install-%s' % version, '/usr/bin/easy_install-3',
    ]
    for path in paths:
        if not os.path.exists():
            root = '/usr/local/bin/' + os.path.basename(path)
            cmds.append(['sudo', 'ln', '-s', root, path])

    post_install = True
    for cmd in cmds:
        log.info(" ".join(cmd))
        with open(os.devnull, 'wb') as devnull:
            return_code = subprocess.call(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=devnull)
        if return_code != 0:
            log.error(color("Unable to run %r" % ' '.join(cmd), 'red'))
            post_install = False
            break
    if not post_install:
        log.error(color("Unable to post-install python", 'red'))
        return

    log.info(color("Python %s installed" % version, 'green'))


def main(args):
    """This is the main script."""
    start = time.time()
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(len(levels) - 1, args.verbose)]
    logging.basicConfig(level=level, format="%(levelname)-8s %(message)s")

    logging.info(color('Starting stack builder install', 'cyan'))

    # These are min required type checks
    pre_checks = [check_os_type, check_sudo_available, check_sudo_access]
    failing_checks = []
    for check in pre_checks:
        kwargs = {'log': logging}
        try:
            check_status, message = check(args, **kwargs)
        except Exception as err:
            logging.error(color("Unable to run check %r - %r" % (str(check), err), 'red'))
            failing_checks.append(check)
            continue
        if check_status:
            logging.info(color(message, 'green'))
        else:
            logging.error(color(message, 'red'))
            failing_checks.append(check)

    if failing_checks:
        return "Missing bare minimum requirements.  Please correct the above errors."

    have_python3, _ = check_python3()
    if not have_python3:
        logging.warning(color("Missing Python3.  This will get installed", "yellow"))


    # More


    if not have_python3:
        start = datetime.datetime.now()
        msg = "Installing python 3 - Patience this can take a bit starting %s" % start
        logging.info(color(msg, 'cyan'))
        install_python3(log=logging)






if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stack Builder install script')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Verbosity')
    parser.add_argument('--no-input', action='store_true', default=False, required=False,
                        help='No input required - just do the right thing.')
    sys.exit(main(parser.parse_args()))
