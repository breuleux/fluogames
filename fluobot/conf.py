from __future__ import with_statement

import re
import os
from copy import copy
import util

assignment_pattern = re.compile('^([a-zA-Z0-9_]*) *=.*$')


class BoolOption(object):

    def __init__(self, description = ""):
        self.description = description

    def filter(self, v):
        if v in ('y', 'yes', 'true', 'True', '1', 1): return True
        if v in ('n', 'no', 'false', 'False', '0', 0): return False
        raise ValueError('Cannot convert %s to boolean.' % v)

    def represent(self, v):
        return repr(v)
    

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


class PathOption(object):

    def __init__(self, description = ""):
        self.description = description

    def filter(self, v):
        return os.path.realpath(os.path.expanduser(v))

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
#         curpath = os.path.curdir
        with util.indir(path):
#             try:
            d = {}
            execfile(file, {}, d)
            d = self.filter_all(d)
#             finally:
#                 os.chdir(curpath)
            for k in self.options:
                if k not in d:
                    raise Exception('Could not find a value for required option: %s' % k)
        return d

    def filter(self, k, v, strict = False):
        if k not in self.options:
            if strict:
                raise Exception('Unknown option: %s' % k)
            else:
                return v 
        return self.options[k].filter(v)
            
    def filter_all(self, d, strict = False):
        new_d = {}
        for k, v in d.iteritems():
            new_d[k] = self.filter(k, v, strict = strict)
        return new_d

    def commit(self, delta, path, file = 'conf.py'):
        delta = self.filter_all(delta, strict = True)
        
        file = os.path.join(path, file)
        newlines = []

        try:
            with open(file, 'r') as f:
                lines = f.readlines()
        except IOError:
            lines = []

        for line in lines:
            match = assignment_pattern.match(line)
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

    def promptfor(self, options, d):
        d = copy(d)
        for option in options:
            o = self.options[option]
            print
            print o.description
            if hasattr(o, 'prompt'):
                prompt = o.prompt
            else:
                prompt = option
            while True:
                if option in d:
                    print  '>', prompt, '[%s]:' % d[option],
                else:
                    print  '>', "%s:" % prompt,
                x = raw_input()
                if x == "":
                    if option in d:
                        x = d[option]
                    else:
                        print 'This field is required. Please enter something.'
                        continue
                try:
                    v = o.filter(x)
                    d[option] = v
                    break
                except Exception, e:
                    print e.message
        d = self.filter_all(d)
        return d






