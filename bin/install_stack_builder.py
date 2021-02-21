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
import logging
import os
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


def main(args):
    """This is the main script."""
    start = time.time()
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(len(levels) - 1, args.verbose)]
    logging.basicConfig(level=level, format="%(levelname)-8s %(message)s")

    logging.info(color('Starting stack builder install', 'cyan'))

    # These are min required type checks
    pre_checks = [check_sudo_available, check_sudo_access]
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





if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stack Builder install script')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Verbosity')
    parser.add_argument('--no-input', action='store_true', default=False, required=False,
                        help='No input required - just do the right thing.')
    sys.exit(main(parser.parse_args()))
