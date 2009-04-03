
import re
import os

assignment_pattern = re.compile('^([a-zA-Z0-9_]*) *=.*$')


class BoolOption(object):

    def __init__(self, description = ""):
        self.description = description

    def filter(self, v):
        if v in ('y', 'yes'): return True
        if v in ('n', 'no'): return False
        return bool(v)
        

class StringOption(object):

    def __init__(self, min_length = None, max_length = None, validator = None, description = ""):
        self.min_length = min_length
        self.max_length = max_length
        self.validator = validator
        self.description = description

    def filter(self, v):
        s = "" if v is None else str(v)
        if self.min_length is not None and len(s) < self.min_length:
            raise ValueError('length must be superior or equal to %s (%s)' % (self.min_length, v))
        elif self.max_length is not None and len(s) > self.max_length:
            raise ValueError('length must be inferior or equal to %s (%s)' % (self.max_length, v))
        if self.validator is not None and not self.validator(s):
            raise ValueError('%s is invalid: %s' % (v, self.validator.__doc__))
        return s

    def represent(self, v):
        return repr(v)


class NumericOption(object):

    def __init__(self, cast, min = None, max = None, description = ""):
        self.cast = cast
        self.min = min
        self.max = max
        self.description = description

    def filter(self, v):
        i = self.cast(v)
        if self.min is not None and i < self.min:
            raise ValueError('%s must be superior or equal to %s: %s' % (self.cast.__name__, self.min, v))
        elif self.max is not None and i > self.max:
            raise ValueError('%s must be inferior or equal to %s: %s' % (self.cast.__name__, self.max, v))
        return i

    def represent(self, v):
        return repr(v)


class ObjectOption(object):

    def __init__(self, base_class = None, description = ""):
        self.base_class = base_class
        self.description = description

    def filter(self, v):
        if self.base_class is not None and not isinstance(v, self.base_class):
            raise TypeError('%s is not of expected type %s' % (v, self.base_class))
        return v

    def represent(self, v):
        raise ValueError('Cannot represent %s (edit conf file yourself)' % v)


class Configurator(object):

    def __init__(self, **options):
        self.options = options

    def load(self, path, file = 'conf.py'):
        curpath = os.path.curdir()
        os.chdir(path)
        try:
            d = {}
            execfile(file, globals = d, locals = {})
            d = self.filter_all(d)
            return d
        finally:
            os.chdir(curpath)

    def filter(self, k, v):
        if k not in self.options:
            raise Exception('Unknown option: %s' % k)
        return self.options[k].filter(v)
            
    def filter_all(self, d):
        new_d = {}
        for k, v in d.iteritems():
            new_d[k] = self.filter(k, v)
        return new_d

    def commit(self, delta, path, file = 'conf.py'):
        delta = self.filter_all(delta)
        
        file = os.path.join(path, file)
        newlines = []

        try:
            with open(file, 'r') as f:
                lines = f.readlines()
        except IOError:
            lines = []

        for line in lines:
            match = assignment_pattern.match(line):
            if match:
                k = match.groups()[0]
                if k in delta and k in self.options:
                    v = delta.pop(k)
                    newlines.append('%s = %s\n' % (k, self.options[k].represent(v)))
                    continue
            newlines.append(line)
            
        for k, v in delta.iteritems():
            opt = self.options[k]
            newlines.append('\n')
            for line in opt.description.split('\n'):
                newlines.append('# %s\n' % line)
            newlines.append('%s = %s\n' % (k, opt.represent(v)))

        with open(file, 'w') as f:
            f.writelines(newlines)


conf = Configurator(
    root = StringOption(description = """
The root of the configuration and the database(s) used by the bot
and the games. Running "fluobot run" with no arguments will by
default use the configuration in ~/.fluobot/conf.py, but you may
pass a different configuration directory or file if you wish."""
                        )
    network = StringOption(min_length = 1, description = """
Network that the bot should connect to."""
                           )
    channel = StringOption(min_length = 1, description = """
Channel that the bot should join."""
                           )
    nickname = StringOption(min_length = 1, description = """
Nickname of the bot"""
                            )
    nickpass = StringOption(description = """
Password for the bot's nickname"""
                            )
    nicksuffix = StringOption(description = 
"""Suffix to append to the nickname if it is already occupied (could be
added multiple times). The bot will try to use the same pass."""
                              )
    reconnect = BoolOption(description = 
"""If reconnect is True, the bot will automatically try to connect to
the network again if it is disconnected."""
                             )
    autoghost = BoolOption(description =
"""If its nickname is taken and autoghost is True, the bot will
automatically try to ghost it (forcefully disconnect it) and change
back to its original nickname."""
                             )
    prefix = StringOption(description =
"""Default prefix for commands when entered in a channel. If set to
None, there will be no prefix."""
                          )
    auth = StringOption(description =
"""
Module to use to identify nicknames to an account and
to handle their permissions.
fluobot.auth.natural requires no logging in and uses
 operator status in order to grant permissions"""
                        )
    )

defaults = dict(
    root = "~/.fluobot",
    network = "",
    channel = "",
    nickname = "",
    nickpass = "",
    nicksuffix = '_',
    reconnect = 'y',
    autoghost = 'y',
    prefix = "!",
    auth = "fluobot.auth.natural"
    )


conf.commit(defaults, '.', 'blablabla.py')



