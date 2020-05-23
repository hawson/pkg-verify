# mtree "things"

class Thing:

    def __init__(self, path=None, attrs=None):

        self.path = path
        self.attr = {}

        if attrs is not None:
            for k,w in attrs.items():
                self.attr[k] = w


    def __repr__(self):
        string = "Path: {}".format(self.path)
        for a,v in self.attr.items():
            string +="\n{}: {}".format(a, v)

        return string
