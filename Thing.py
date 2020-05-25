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

    file_type = {
        'dir':    0o040000, # directory
        'char':   0o020000, # character device
        'block':  0o060000, # block device
        'file':   0o100000, # regular file
        'fifo':   0o010000, # fifo (named pipe)
        'link':   0o120000, # symbolic link
        'socket': 0o140000, # socket file
    }

    def __init__(self, path=None, attrs=None, altroot=None, ignore_dir_mtime=False):

        if altroot:
            self.path = altroot + '/' + path.lstrip('.')
        else:
            self.path = path.lstrip('.')

        self.attr = {}
        self.failures = []
        self.ignore_dir_mtime = ignore_dir_mtime

        if attrs is not None:
            for k,w in attrs.items():
                self.attr[k] = w

        try:
            self.attr['type'] = Thing.file_type[self.attr['type']]

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
            logging.debug("Stored   {type}: {digest}".format(type=h, digest=stored))
            logging.debug("Computed {type}: {digest}".format(type=h, digest=computed))
            if stored != computed:
                mismatch += 1

        if mismatch:
            return False

        return True


    def check_uid(self):
        if self.osstat.st_uid == int(self.attr['uid']):
            return True
        logging.info('UID mismatch {} != {}'.format(self.attr['uid'], stat.st_uid))
        return False


    def check_gid(self):
        if self.osstat.st_gid == int(self.attr['gid']):
            return True
        logging.info('GID mismatch {} != {}'.format(self.attr['gid'], stat.st_gid))
        return False


    def check_mtime(self):
        if self.ignore_dir_mtime and self.attr['type'] == Thing.file_type['dir']:
            return True

        if self.osstat.st_mtime == float(self.attr['time']):
            return True
        logging.info('mtime mismatch {} != {}'.format(self.attr['time'], self.osstat.st_mtime))
        return False


    def check_mode(self):
        lmode = stat.S_IMODE(self.osstat.st_mode & 0o007777)
        lftype = stat.S_IFMT(self.osstat.st_mode & 0o170000)

        mode = self.attr['mode']
        ftype = self.attr['type']

        logging.info("stat mode: %06s / %06s" % (lmode, self.attr['mode']))
        logging.info("stat type: %06s / %06s" % (lftype, ftype))

        if mode == lmode:
            return True

        logging.info('mode mismatch {} != {}'.format(mode, lmode))
        return False


    def check_device(self):
        '''Check device file major/minor numbers.  Unused: always True.'''
        return True


    def check_capabilities(self):
        '''Check capabilities.  Unused: always True.'''
        return True


    def check_link(self):
        '''Not yet implemnted'''
        return True

    def check_size(self):
        if self.attr['type'] != 'file':
            return True

        if self.osstat.st_size == int(self.attr['size']):
            return True

        logging.info('size mismatch {} != {}'.format(self.attr['size'], stat.st_size))
        return False




    def check_metadata(self):

        mode = {}
        result = True

        logging.debug(self.osstat)
        logging.debug(self.attr)
        # Only check size and mtime on files
        if self.attr['type'] == 'file' and os.path.isfile(self.path):
            mode['size'] = self.check_size(live_statinfo)
            mode['mtime'] = self.check_mtime(live_statinfo)


        return result, mode


# from RPM:
#    The format of the output is  a  string  of  9  characters,  a  possible
#    attribute marker:
#
#    c %config configuration file.
#    d %doc documentation file.
#    g %ghost file (i.e. the file contents are not included in the package payload).
#    l %license license file.
#    r %readme readme file.
#
#    from  the  package  header,  followed  by the file name.  Each of the 9
#    characters denotes the result of a comparison of  attribute(s)  of  the
#    file  to  the  value of those attribute(s) recorded in the database.  A
#    single "." (period) means the test passed, while a single "?" (question
#    mark)  indicates the test could not be performed (e.g. file permissions
#    prevent reading). Otherwise, the  (mnemonically  emBoldened)  character
#    denotes failure of the corresponding --verify test:
#
#    S file Size differs
#    M Mode differs (includes permissions and file type)
#    5 digest (formerly MD5 sum) differs ("5" for md5sum, "2" for sha256", and "7" for both)
#    D Device major/minor number mismatch (NOT USED)
#    L readLink(2) path mismatch
#    U User ownership differs
#    G Group ownership differs
#    T mTime differs
#    P caPabilities differ  (NOT USED)'''

    def verify(self):
        '''Returns True if all metadata matches correctly, for certain definitions of "all".'''
        logging.info("Verifying %s" % self.path)


        try:
            self.osstat = os.lstat(self.path)

        except OSError as exc:
            logging.error("Failed to call lstat() on %s: %s" % (self.path, exc))
            sys.exit(1)


        self.failures.append( '.' if self.check_size() else 'S')   # size
        self.failures.append( '.' if self.check_mode() else 'M')   # mode
        self.failures.append( '.' if self.check_hashes() else '5') # digests
        self.failures.append( '.' if self.check_device() else 'S')   # device major/minor (unused)
        self.failures.append( '.' if self.check_link() else 'L')   # Link target mismatch
        self.failures.append( '.' if self.check_uid() else 'U')   # user
        self.failures.append( '.' if self.check_gid() else 'G')   # group
        self.failures.append( '.' if self.check_mtime() else 'T')   # mtime
        self.failures.append( '.' if self.check_capabilities() else 'P')   # capabilities (unused)

        if self.attr['type'] == 'file':
            if not self.check_hashes():
                self.failures.append('checksums')

        print("{}     {}".format(''.join(self.failures), self.path))

        if self.failures:
            return False, self.failures

        return True, self.failures



