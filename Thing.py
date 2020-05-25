# mtree "things"

import logging
import hashlib
import os
import stat


def filehash(file_to_hash, hashtype):

    if hashtype in ('md5digest', 'md5', 'md5sum'):
        h = hashlib.md5()
    elif hashtype in ('sha256digest', 'sha256', 'sha256sum'):
        h = hashlib.sha256()
    else:
        logging.error('Missing hash function %s' % hashtype)
        return None

    BLOCKSIZE=2**13
    with open(file_to_hash, 'rb') as f:
        block = f.read(BLOCKSIZE)
        while len(block) > 0:
            h.update(block)
            block = f.read(BLOCKSIZE)

    return h.hexdigest()



class Thing:

    file_types = {
        'dir':    0o040000, # directory
        'char':   0o020000, # character device
        'block':  0o060000, # block device
        'file':   0o100000, # regular file
        'fifo':   0o010000, # fifo (named pipe)
        'link':   0o120000, # symbolic link
        'socket': 0o140000, # socket file
    }

    def __init__(self, path=None, attrs=None, altroot=None):

        if altroot:
            self.path = altroot + '/' + path.lstrip('.')
        else:
            self.path = path.lstrip('.')

        self.attr = {}

        if attrs is not None:
            for k,w in attrs.items():
                self.attr[k] = w

        try:
            self.attr['type'] = Thing.file_types[self.attr['type']]

        except KeyError:
            logging.error("unknown type=%s in mtree file" % self.attr['type'])
            sys.exit(1)

        # store mode as INTEGER.  We will compare/present as octal later
        self.attr['mode'] = int(self.attr['mode'], 8)

        logging.info(self.attr)


    def __repr__(self):
        string = "\nPath: {}\n".format(self.path)
        for a,v in self.attr.items():
            string += "{}: {}\n".format(a, v)

        return string



    def check_hashes(self):

        mismatch = 0
        for h in [ x for x in self.attr if str(x).endswith('digest') ]:
            stored = self.attr[h]
            computed = filehash(self.path, h)
            print("Stored   {type}: {digest}".format(type=h, digest=stored))
            print("Computed {type}: {digest}".format(type=h, digest=computed))
            if stored != computed:
                mismatch += 1

        return True if mismatch == 0 else False


    def check_uid(self, stat):
        if stat.st_uid == int(self.attr['uid']):
            return True
        logging.info('UID mismatch {} != {}'.format(self.attr['uid'], stat.st_uid))
        return False


    def check_gid(self, stat):
        if stat.st_gid == int(self.attr['gid']):
            return True
        logging.info('GID mismatch {} != {}'.format(self.attr['gid'], stat.st_gid))
        return False


    def check_mtime(self, stat):
        if stat.st_mtime == float(self.attr['time']):
            return True
        logging.info('mtime mismatch {} != {}'.format(self.attr['time'], stat.st_mtime))
        return False


    def check_mode(self, livestat):
        lmode = stat.S_IMODE(livestat.st_mode & 0o007777)
        lftype = stat.S_IFMT(livestat.st_mode & 0o170000)

        mode = self.attr['mode']
        ftype = self.attr['type']

        logging.info("stat mode: %06s / %06s" % (lmode, self.attr['mode']))
        logging.info("stat type: %06s / %06s" % (lftype, ftype))

        if mode == lmode:
            return True

        logging.info('mode mismatch {} != {}'.format(mode, lmode))
        return False


    def check_size(self, stat):
        if stat.st_size == int(self.attr['size']):
            return True
        logging.info('size mismatch {} != {}'.format(self.attr['size'], stat.st_size))
        return False




    def check_metadata(self):

        mode = {}
        result = True

        live_statinfo = os.stat(self.path)

# INFO:root:{'type': 'file', 'uid': '0', 'gid': '0', 'mode': '644', 'time': '1573667866.0', 'size': '16262', 'md5digest': '95e83c46958f6395f746c80cc6799e76', 'sha256digest': '77304005ceb5f0d03ad4c37eb8386a10866e4ceeb204f7c3b6599834c7319541'}

        logging.debug(live_statinfo)
        logging.debug(self.attr)
        mode['uid'] = self.check_uid(live_statinfo)
        mode['gid'] = self.check_gid(live_statinfo)
        mode['mode'] = self.check_mode(live_statinfo)
        mode['mtime'] = self.check_mtime(live_statinfo)

        if self.attr['type'] == 'file' and os.path.isfile(self.path):
            mode['size'] = self.check_size(live_statinfo)

        return result, mode


    def verify(self):
        print()
        logging.info("Verifying %s" % self.path)

        failures = ()

        if self.attr['type'] == 'file':
            if not self.check_hashes():
                failures.append('checksums')

        metadata_rc, mode = self.check_metadata()
        if not metadata_rc:
            failures.append(mode)

        if failures:
            logging.error("failures: " % failures)
            return False

        return True



