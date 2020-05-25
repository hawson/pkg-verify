#!/usr/bin/env python3

import os
import sys
import argparse
import re
import subprocess
import logging
import gzip

from Mtree import Mtree

# always log WARN-ERR-CRIT
args_verbose = 3
verbose_level = (30 - args_verbose*10)
logging.basicConfig(level=verbose_level)



def mtree_path(pkg, version):
    return '/'.join(['/var/lib/pacman/local', pkg + '-' + version, 'mtree'])

def pkg_version(pkg):
    logging.info("Getting version for %s" % pkg)
    try:
        cmd = ['/usr/bin/pacman', '-Q', pkg]
        logging.debug("Running %s" % cmd)
        output = subprocess.run(cmd, stdout=subprocess.PIPE, check=False, encoding='utf-8').stdout.strip().split(' ')

    except SubprocessErrror as exc:
        logging.error("Failed to run %s: %s" % ( ' '.join(cmd), exc))
        sys.exit(1)
        
    return output


if '__main__' == __name__:

    logging.info("Starting")

    pkg, version = pkg_version(sys.argv[1])
    mpath = mtree_path(pkg,version)

    logging.debug("%s %s %s" % ( pkg, version, mpath ))

    mtree = Mtree(mpath)

    print(type(mtree))

    for entry in iter(mtree.objects):

        verified, failures = entry.verify()

