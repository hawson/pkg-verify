import gzip
import re

from Thing import Thing


def parse_mtree(mtree_file):
    gz = gzip.open(mtree_file, mode="rt", encoding='utf-8')

    for line in gz:
        print(line)

        if not re.match(r'^\./', line):
            continue

        path, attrstr = line.split(' ', maxsplit=1)

        attribs = {}
        for a in attrstr.split(' '):
            k,v = a.split('=')
            attribs[k] = v

        T = Thing(path, attrs=attribs)
        print(T)

class Mtree:

    def __init__(self, mtree_file):
        self.mtree_file = mtree_file
        self.objects = parse_mtree(self.mtree_file)



    

            
