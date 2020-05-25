import gzip
import re
import logging


from Thing import Thing


##mtree
#/set type=file uid=0 gid=0 mode=644
#./.BUILDINFO time=1581622860.0 size=4891 md5digest=85c4a154d55cc9a3856d4e368b293259 sha256digest=9dfdeb2e1b67043e31d7855a37dfd00b8839dc9ca300b9273ce75429f04867bc
#./.PKGINFO time=1581622860.0 size=584 md5digest=bf536e1ff9a04547133103de718d680f sha256digest=d09be33c9b92f8d9561f29db0b6d903040b6a5f53ea065dfd828ed035606adc4

def parse_mtree(mtree_file):
    gz = gzip.open(mtree_file, mode="rt", encoding='utf-8')

    defaults = {}
    objects = []

    for line in gz:


        logging.debug(line.strip())
        line = re.sub(r'\s*#.*', '', line.strip())

        if line == '':
            logging.debug('Empty line')
            continue

        # the /set lines update the default attributes
        m = re.match(r'^/set\s+(.*)', line)
        if m:
            for a in re.split(r'\s+', m.group(1)):
                k, v = a.split('=')
                defaults[k] = v
            logging.debug('new defaults: %s', str(defaults))
            continue

        # handle /unset
        m = re.match(r'^/unset\s+(.*)', line)
        if m:
            for a in re.split(r'\s+', m.group(1)):
                defaults.pop(a)
                print(defaults)
            continue


        # "data" line....
        path, attrstr = line.split(' ', maxsplit=1)

        # skip these
        if path in ('./.BUILDINFO', './.PKGINFO', './.INSTALL', './.CHANGELOG'):
            continue

        # default type.
        attribs = dict(defaults)
        attribs['type'] = 'file'

        for a in attrstr.split(' '):
            k, v = a.split('=')
            attribs[k] = v

        T = Thing(path, attrs=attribs, ignore_dir_mtime=True)
        objects.append(T)
        #print(T)

    return objects




class Mtree():

    def __init__(self, mtree_file):
        self.mtree_file = mtree_file
        self.index = 0
        self.objects = parse_mtree(self.mtree_file)
        self.length = len(self.objects)


    def __iter__(self):
        self.index = 0
        yield self

    def __next__(self):
        if self.index > self.length:
            yield StopIteration

        result = self.objects[self.index]
        self.index += 1
        yield result

