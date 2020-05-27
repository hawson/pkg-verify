#!/usr/bin/env python3

import sys
import argparse
import subprocess
import logging

from Mtree import Mtree


def mtree_path(pkg, version):
    return '/'.join(['/var/lib/pacman/local', pkg + '-' + version, 'mtree'])

def pkg_version(pkg):
    logging.debug("Getting version for %s", pkg)
    try:
        cmd = ['/usr/bin/pacman', '-Q', pkg]
        logging.debug("Running %s", cmd)
        output = subprocess.run(cmd, stdout=subprocess.PIPE, check=False, encoding='utf-8').stdout.strip().split(' ')

    except SubprocessError as exc:
        logging.error("Failed to run %s: %s", ' '.join(cmd), exc)
        sys.exit(1)
        
    return output


if __name__ == '__main__':


    parser = argparse.ArgumentParser(description='''Verify pacman pacmages, including checksums.''')
    parser.add_argument('-v', '--verbose', action='count', help='Be verbose (multiples okay)')
    parser.add_argument('-R', '--altroot', action='store', help='set alternate root directory')
    parser.add_argument('-T', '--check-dir-mtime', action='count', default=False, help='Check mtimes on directories (normally ignored)')

    try:
        parsed_options, remaining_args = parser.parse_known_args()

    except SystemExit as exc:
        print("Failed parsing arguments: %s" % exc)
        sys.exit(2)
        

    verbose_value = 0 if parsed_options.verbose is None else parsed_options.verbose
    LOG_LEVEL = (30 - verbose_value * 10)
    logging.basicConfig(format='%(asctime)-15s [%(levelname)s] %(message)s', level=LOG_LEVEL)


    logging.debug("Starting")

    RC = 0

    for arg in remaining_args:
        pkg, version = pkg_version(arg)
        mpath = mtree_path(pkg, version)

        logging.debug("%s %s %s", pkg, version, mpath)

        mtree = Mtree(mpath)


        for entry in iter(mtree.objects):

            verified, failure_str = entry.verify()
            if not verified:
                RC = 1

            if LOG_LEVEL < 30 or not failure_str.startswith('.........'):
                print(failure_str)


    sys.exit(RC)
