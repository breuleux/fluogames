
import inspect
import re
import os



class indir(object):

    def __init__(self, dir):
        self.dir = dir
    
    def __enter__(self):
        self.curdir = os.curdir
        os.chdir(self.dir)

    def __exit__(self, type, value, traceback):
        os.chdir(self.curdir)

        

real_reload = reload
def resolve(name, try_import = True, reload = False):
    """
    Resolve a string of the form X.Y...Z to a python object by repeatedly using getattr, and
    __import__ to introspect objects (in this case X, then Y, etc. until finally Z is loaded).

    """
    symbols = name.split('.')
    builder = __import__(symbols[0])
    try:
        for sym in symbols[1:]:
            try:
                builder = getattr(builder, sym)
            except AttributeError, e:
                if try_import:
                    __import__(builder.__name__, fromlist=[sym])
                    builder = getattr(builder, sym)
                else:
                    raise e
    except (AttributeError, ImportError), e:
        raise type(e)('Failed to resolve compound symbol %s' % name, e)
    if reload:
        builder = real_reload(builder)
    return builder


def parent_function():
    return inspect.stack()[2]



class UsageError(Exception):
    def __init__(self, message=None):
        super(UsageError, self).__init__(message)
typeerror_regexp = re.compile('.*takes .* ([0-9]*) arguments? \\(([0-9]*) given\\)')


class Stateful(object):
    def __new__(cls, *args, **kwargs):
        rval = object.__new__(cls)
        rval.switch(cls, False, False)
        return rval
    def on_switch_in(self):
        pass
    def on_switch_out(self):
        pass
    def switch(self, state, switch_in = True, switch_out = True):
        if switch_out:
            self.on_switch_out()
        self.__class__ = state
        if switch_in:
            self.on_switch_in()
    def get_state(self):
        return self.__class__


