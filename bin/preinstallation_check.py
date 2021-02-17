#!/bin/env python

# curl -sSL https://github.com/icmanage/rc-files/raw/main/bin/preinstallation_check.py | python - --type vtrq-vda -vv

import argparse
import logging
import os
import re
import sys
import time
import subprocess


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
    elif os_data.get('ID') == 'ubuntu':
        if os_data['VERSION'] != "18":
            return False, 'Ubuntu version %s unsupported' % os_data['VERSION']
        return True, 'Ubuntu version %s supported' % os_data['VERSION']
    elif os_data.get('ID') is None:
        return False, "Unable to identify ID and or VERSION from /etc/os-release"


def check_sudo_available(*_args, **_kwargs):
    """Verify sudo availability"""
    return_code = subprocess.call(['which', 'sudo'], stdout=subprocess.PIPE)
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


def check_nvme_disk(*_args, **_kwargs):
    """Verify that we have an NVME disk"""
    command = ['lsblk', '-d', '-n', '-o', 'name']
    output = subprocess.check_output(command)
    if 'nvme' in output:
        return True, "NVME exists.  You have an NVME disk"
    return False, "NVME disk NOT available.  Wrong hardware we need an NVME disk."


def check_holodeck_config_exists(args, log=None, **_kwargs):
    """Does the halodeck config file exist"""
    if not os.path.exists(args.config):
        return False, "HOLODECK_CONFIGURATION_FILE file %r does not exist" % args.config
    read_config(os.environ.get('HOLODECK_CONFIGURATION_FILE'), log=log)
    return True, "Holodeck configuration %r exists and can be read / parsed" % args.config


def _test_writeable_directory(variable_name, ):
    config = read_config(os.environ.get('HOLODECK_CONFIGURATION_FILE'), report=False)
    test_file = os.path.join(config[variable_name], '.empty_file')
    return_code = subprocess.call(['touch', test_file], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
    if return_code == 1:
        return False, "Unable to write to %s (%s) as defined in " \
                      "HOLODECK_CONFIGURATION_FILE" % (variable_name, config[variable_name])
    subprocess.call(['rm', test_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return True, "%s (%s) as defined in HOLODECK_CONFIGURATION_FILE is " \
                 "writeable" % (variable_name, config[variable_name])


def check_writeable_vtrq_backingstore(_args, **_kwargs):
    """Does the halodeck config file exist"""
    return _test_writeable_directory('VTRQ_BACKING_STORE')


def check_writeable_vda_backingstore(_args, **_kwargs):
    """Does the halodeck config file exist"""
    return _test_writeable_directory('VDA_BACKING_STORE')


def check_writeable_install_directory(_args, **_kwargs):
    """Does the halodeck config file exist"""
    return _test_writeable_directory('PC_INSTALL_AREA')


def check_writeable_install_log_directory(_args, **_kwargs):
    """Does the halodeck config file exist"""
    return _test_writeable_directory('PC_LOG_DIR')


def check_installed_packages(_args, log=None, **_kwargs):
    os_data = read_config('/etc/os-release', separator='=', log=log, report=False)
    missing = []
    if os_data.get('ID') == 'amzn':
        packages = ['amazon-linux-extras', 'yum-utils', 'device-mapper-persistent-data',
                    'lvm2', 'm4', 'docker']
        for package in packages:
            command = ['yum', 'list', 'installed', package]
            return_code = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if return_code == 1:
                missing.append(package)
    elif os_data.get('ID') == 'rhel':
        packages = ['docker']
        for package in packages:
            command = ['yum', 'list', 'installed', package]
            return_code = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if return_code == 1:
                missing.append(package)
    if missing:
        return False, "The following system packages are missing: %s" % ", ".join(missing)
    return True, "All required system packages installed."


def check_user_in_docker_group(_args, **_kwargs):
    output = subprocess.check_output(['groups'])
    if 'docker' not in output:
        return False, "User is not part of the docker group."
    return True, "User is part of the docker group."


def color(msg, color='default', bold=False):
    """Color some text"""
    color_dict = {'default': 0, 'black': 30, 'red': 31, 'green': 32,
                  'yellow': 33, 'blue': 34, 'magenta': 35, 'cyan': 36,
                  'white': 37, }
    if not color_dict.get(color):
        logging.warning('Unknown color "{}"'.format(color))
    if '{}'.format(os.environ.get('NO_COLOR')) == '1':
        return msg
    return '\033[{};{}m{}\033[0m'.format(int(bold), color_dict.get(color, 0), msg)


def get_checks(system_type):
    """Collect the checks needed"""
    checks = [check_os_type, check_sudo_available, check_holodeck_config_exists]
    if 'vtrq' in system_type:
        checks.append(check_sudo_access)
        checks.append(check_nvme_disk)
        checks.append(check_writeable_vtrq_backingstore)
        checks.append(check_installed_packages)

    if 'vda' in system_type:
        checks.append(check_user_in_docker_group)
        checks.append(check_writeable_vda_backingstore)

    checks.append(check_writeable_install_directory)
    checks.append(check_writeable_install_log_directory)
    return checks


def main(args):
    """Main script to run"""
    start = time.time()
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(len(levels) - 1, args.verbose)]
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)8s %(message)s", datefmt='%H:%M:%S')

    checks = get_checks(args.type)
    logging.info('Starting %d pre-checks on %s', len(checks), args.type)

    os.environ['HOLODECK_CONFIGURATION_FILE'] = args.config

    failing_checks = []
    for check in checks:
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

    data = dict(elapsed_time=round((time.time() - start), 2), total_checks=len(checks),
                failing_checks=len(failing_checks), type=args.type)
    if failing_checks:
        msg = '\nFailed! System pre-check for %(type)s failed %(failing_checks)d/' \
              '%(total_checks)s checks in %(elapsed_time)s secs' % data
        if not args.verbose:
            msg += " Add -vv to see specific failing checks"
        print(color(msg, 'red'))
        return 255

    msg = '\nAll passed! System verified %(total_checks)d %(type)s ' \
          'checks in %(elapsed_time)s secs' % data
    print(color(msg, 'green'))


if __name__ == '__main__':
    _def_conf = os.path.join(os.environ.get('HOME'), "holodeck.cfg")
    default_config = os.environ.get('HOLODECK_CONFIGURATION_FILE', _def_conf)

    parser = argparse.ArgumentParser(description='Pre-check the system')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Verbosity')
    parser.add_argument('-c', '--config', action='store',
                        default=default_config, help='Holodeck configuration')
    parser.add_argument('-t', '--type', action='store', choices=['vtrq', 'vtrq-vda'],
                        help="System type that needs checking")

    sys.exit(main(parser.parse_args()))
