#!/bin/env python

# curl -sSL --retry 5 https://github.com/icm_manage/rc-files/raw/master/bin/preinstallation_check.py  | sh -s -- -a axis -c production -vvv
# -s -- -a axis -c production -vvv
import argparse
import logging
import os
import sys
import time
import subprocess


def check_sudo_access():
    """Verify sudo access"""
    return_code = subprocess.call(['sudo', '-V'], stdout=subprocess.PIPE)
    if return_code == 0:
        return True, "Passing sudo access"
    return False, "Failing sudo access"


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
    checks = []
    if 'vtrq' in system_type:
        checks.append(check_sudo_access)

    return checks


def main(args):
    start = time.time()
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(len(levels) - 1, args.verbose)]
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(message)s", datefmt='%H:%M:%S')

    checks = get_checks(args.type)
    logging.info('Starting %d pre-checks', len(checks))

    for check in checks:
        try:
            check_status, message = check()
        except Exception as err:
            logging.error(color("Unable to run check %r - %r" % (str(check), err), 'red'))
            continue
        if check_status:
            logging.error(color(message, 'red'))
        else:
            logging.info(color(message, 'green'))

    data = dict(elapsed_time=time.time() - start)
    logging.info('All done! System verified in %(elapsed_time)s', data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pre-check the system')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Verbosity')
    parser.add_argument('-t', '--type', action='store', choices=['vtrq', 'vtrq-vda'],
                        help="System type that needs checking")

    sys.exit(main(parser.parse_args()))