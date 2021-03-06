# mtree "things"

import logging
import hashlib
import os
import stat
import sys


def filehash(file_to_hash, hashtype):
    '''Computes checksum of a file'''

    if hashtype in ('md5digest', 'md5', 'md5sum'):
        h = hashlib.md5()
    elif hashtype in ('sha256digest', 'sha256', 'sha256sum'):
        h = hashlib.sha256()
    else:
        logging.error('Missing hash function %s', hashtype)
        return None

    BLOCKSIZE = 2**13

    try:
        with open(file_to_hash, 'rb') as f:
            block = f.read(BLOCKSIZE)
            while len(block) > 0:
                h.update(block)
                block = f.read(BLOCKSIZE)

    except OSError as exc:
        # We don't actually care if a file can't be opened; that's
        # probably a permissions error, and thus a valid falure mode
        #logging.error("Failed opening %s: %s" %(file_to_hash, exc))
        return None


    return h.hexdigest()


class Thing:
    '''Interpret and manage mtree infomration about files on the filesystem'''

    file_type = {
        'dir':    0o040000, # directory
        'char':   0o020000, # character device
        'block':  0o060000, # block device
        'file':   0o100000, # regular file
        'fifo':   0o010000, # fifo (named pipe)
        'link':   0o120000, # symbolic link
        'socket': 0o140000, # socket file
    }

    # invert
    for k in list(file_type.keys()):
        file_type[file_type[k]] = k


    def __init__(self, path=None, attrs=None, altroot=None, ignore_dir_mtime=False):

        if altroot:
            self.path = altroot + '/' + path.lstrip('.')
        else:
            self.path = path.lstrip('.')

        self.attr = {}
        self.failures = []

        # directories often have mtimes update, outside of the control of a package
        # and can cause a lot of noise in "popular" directories, like /usr/man/*
        # so this option lets us ignore the mtime metdata data check.  The option
        self.ignore_dir_mtime = ignore_dir_mtime

        if attrs is not None:
            for k, w in attrs.items():
                self.attr[k] = w

        try:
            self.attr['type'] = Thing.file_type[self.attr['type']]

        except KeyError:
            logging.error("unknown type=%s in mtree file", self.attr['type'])
            sys.exit(1)

        # store mode as INTEGER.  We will compare/present as octal later,
        # this is done because ints are easier to push around than
        # converting back and forth between string representation of octal numbers
        self.attr['mode'] = int(self.attr['mode'], 8)

        logging.debug(self.attr)


    def __repr__(self):
        string = "\nPath: {}\n".format(self.path)
        for a, v in self.attr.items():
            string += "{}: {}\n".format(a, v)

        return string



    def check_hashes(self):

        mismatch = 0

        # check all of the digests, whatever they are
        for h in [x for x in self.attr if str(x).endswith('digest')]:
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
        logging.debug('UID mismatch {} != {}'.format(self.attr['uid'], self.osstat.st_uid))
        return False


    def check_gid(self):
        if self.osstat.st_gid == int(self.attr['gid']):
            return True
        logging.debug('GID mismatch {} != {}'.format(self.attr['gid'], self.osstat.st_gid))
        return False


    def check_mtime(self):
        # we can ignore mtimes on directories, sometimes.
        if self.ignore_dir_mtime and self.attr['type'] == Thing.file_type['dir']:
            return True

        if self.osstat.st_mtime == float(self.attr['time']):
            return True
        logging.debug('mtime mismatch {} != {}'.format(self.attr['time'], self.osstat.st_mtime))
        return False


    def check_mode(self):
        lmode = stat.S_IMODE(self.osstat.st_mode & 0o007777)
        lftype = stat.S_IFMT(self.osstat.st_mode & 0o170000)

        mode = self.attr['mode']
        ftype = self.attr['type']

        logging.debug("stat mode: %06o / %06o", lmode, self.attr['mode'])
        logging.debug("stat type: %06s / %-6s", Thing.file_type[lftype], Thing.file_type[ftype])

        if mode == lmode and ftype == lftype:
            return True

        if mode != lmode:
            logging.debug('mode mismatch %4o != %4o', mode, lmode)

        if ftype != lftype:
            logging.debug('type mismatch {} != {}'.Thing.format(file_type[mode], Thing.file_type[lftype]))

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

        logging.debug('size mismatch {} != {}'.format(self.attr['size'], self.osstat.st_size))
        return False




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
        logging.debug("Verifying %s", self.path)


        try:
            if os.path.exists(self.path):
                self.osstat = os.lstat(self.path)
            else:
                return False, '---------     {}'.format(self.path)

        except OSError as exc:
            logging.error("Failed to call lstat() on %s: %s", self.path, exc)
            sys.exit(1)


        self.failures.append('.' if self.check_size() else 'S')         # size
        self.failures.append('.' if self.check_mode() else 'M')         # mode
        self.failures.append('.' if self.check_hashes() else '5')       # digests
        self.failures.append('.' if self.check_device() else 'S')       # device major/minor (unused)
        self.failures.append('.' if self.check_link() else 'L')         # Link target mismatch
        self.failures.append('.' if self.check_uid() else 'U')          # user
        self.failures.append('.' if self.check_gid() else 'G')          # group
        self.failures.append('.' if self.check_mtime() else 'T')        # mtime
        self.failures.append('.' if self.check_capabilities() else 'P') # capabilities (unused)

        if self.attr['type'] == 'file':
            if not self.check_hashes():
                self.failures.append('checksums')

        rc = max(self.failures) == '.'

        failure_str = "{}     {}".format(''.join(self.failures), self.path)

        return rc, failure_str
