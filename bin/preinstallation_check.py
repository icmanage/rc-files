#!/bin/env python

# curl -sSL https://github.com/icmanage/rc-files/raw/main/bin/preinstallation_check.py | python - --type vtrq-vda -vv

import argparse
import logging
import os
import sys
import time
import subprocess


def get_os_release():
    """This will pull the OS Release data for the OS"""
    if os.path.exists('/etc/os-release'):
        with open('/etc/os-release') as file_obj:
            data = file_obj.readlines()
        results = {}
        for line in data:
            _x = line.split("=")
            key, value = _x[0], "=".join(_x[1:])
            value = value[1:-1] if value.startswith('"') and value.endswith('"') else value
            value = value[1:-1] if value.startswith("'") and value.endswith("'") else value
            results[key] = value
        return results


def check_os_type():
    """Verify our version"""
    os_data = get_os_release()
    if os_data['ID'] == 'amzn':
        if os_data['VERSION'] != "2":
            return False, 'Amazon version %s unsupported' % os_data['VERSION']
        return True, 'Amazon version %s supported' % os_data['VERSION']
    if os_data['ID'] == 'rhel':
        if os_data['VERSION'] not in ["2", "6"]:
            return False, 'Redhat version %s unsupported' % os_data['VERSION']
        return True, 'Redhat version %s supported' % os_data['VERSION']
    if os_data['ID'] == 'ubuntu':
        if os_data['VERSION'] != "18":
            return False, 'Ubuntu version %s unsupported' % os_data['VERSION']
        return True, 'Ubuntu version %s supported' % os_data['VERSION']


def check_sudo_available():
    """Verify sudo availability"""
    return_code = subprocess.call(['which', 'sudo'], stdout=subprocess.PIPE)
    if return_code == 0:
        return True, "Passing sudo availability.  Sudo is available"
    return False, "Failing sudo availability.  Install sudo."


def check_sudo_access():
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


def check_nvme_disk():
    """Verify that we have an NVME disk"""
    command = ['lsblk', '-d', '-n', '-o', 'name']
    output = subprocess.check_output(command)
    if 'nvme' in output:
        return True, "NVME exists.  You have an NVME disk"
    return False, "NVME disk NOT available.  Wrong hardware we need an NVME disk."


def package_checks():
    """Verify we have the right packages installed"""
    return_code = subprocess.call(['sudo', '-V'], stdout=subprocess.PIPE)
    if return_code == 0:
        return True, "Passing sudo access"
    return False, "Failing sudo access"


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
    checks = [check_os_type, check_sudo_available]
    if 'vtrq' in system_type:
        checks.append(check_sudo_access)
        checks.append(check_nvme_disk)

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

    failing_checks = []
    for check in checks:
        try:
            check_status, message = check()
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
        msg = '\nFailed! System pre-check for %(type)s failed %(failing_checks)d checks ' \
              'in %(elapsed_time)s secs' % data
        if not args.verbose:
            msg += " Add -vv to see specific failing checks"
        print(color(msg, 'red'))
        return 255

    msg = '\nAll passed! System verified %(total_checks)d %(type)s ' \
          'checks in %(elapsed_time)s secs' % data
    print(color(msg, 'green'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pre-check the system')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Verbosity')
    parser.add_argument('-t', '--type', action='store', choices=['vtrq', 'vtrq-vda'],
                        help="System type that needs checking")

    sys.exit(main(parser.parse_args()))
