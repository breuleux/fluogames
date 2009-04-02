
from hooks import Hook, HookList, hook
from copy import copy


########################################

class Extender(object):
    def __init__(self):
        self.__registry__ = {}
    def register(self, name, clsprop):
        raise NotImplementedError
    def apply_to_instance(self, instance):
        raise NotImplementedError
    def __copy__(self):
        cpy = self.__class__()
        cpy.__registry__ = dict(self.__registry__)
        return cpy

########################################

class HookExtender(Extender):
    def register(self, name, prop):
        if not isinstance(prop, Hook):
            raise TypeError
        self.__registry__[name] = prop
        return {name: prop}
    def apply_to_instance(self, instance):
        for name, hook in self.__registry__.iteritems():
            setattr(instance, name, hook.specialize(instance))

########################################

class HookListExtender(Extender):
    def register(self, name, prop):
        if not isinstance(prop, HookList):
            raise TypeError
        self.__registry__[name] = prop
        return {name: prop}
    def apply_to_instance(self, instance):
        for name, hooklist in self.__registry__.iteritems():
            setattr(instance, name,
                    hooklist.__class__([h.specialize(instance) for h in hooklist.hooks]))

########################################

class Property(object):
    def __init__(self, propcls, name = None):
        self.propcls = propcls
        self.name = name
    def __setup__(self, obj):
        handler = self.propcls(obj)
        setattr(obj, self.name, handler)
    def __get__(self, obj, type):
        return getattr(obj, self.name).value
    def __set__(self, obj, value):
        getattr(obj, self.name).value = value

class PropertyExtender(Extender):
    def register(self, name, prop):
        if not isinstance(prop, Property):
            raise TypeError
        prop.name = "_" + name
        self.__registry__[name] = prop
        return {name: prop}
    def apply_to_instance(self, instance):
        for name, prop in self.__registry__.iteritems():
            prop.__setup__(instance)

########################################


class ExtensibleMC(type):

    def __init__(cls, name, bases, dct):
        cls.__extenders__ = dct.get('__extenders__', [])
        for base in bases:
            cls.__extenders__ += map(copy, getattr(base, '__extenders__', []))
        for attr, value in dct.iteritems():
            # Technically, the attributes are already all in the class
            # but __setattr__ has additional behavior
            if attr != '__new__':
                setattr(cls, attr, value)

    def __setattr__(cls, attr, value):
        for extender in cls.__extenders__:
            try:
                dct = extender.register(attr, value)
            except TypeError:
                continue
            for attr2, value2 in dct.iteritems():
                type.__setattr__(cls, attr2, value2)
            break
        else:
            type.__setattr__(cls, attr, value)


class Extensible(object):

    __metaclass__ = ExtensibleMC
    __extenders__ = [HookExtender(), HookListExtender(), PropertyExtender()]
    
    def __new__(cls, *args, **kwargs):
        self = object.__new__(cls, *args, **kwargs)
        for extender in cls.__extenders__:
            extender.apply_to_instance(self)
        return self


########################################


def extend(cls):
    def decorator(f):
        setattr(cls, f.__name__, f)
        return f
    return decorator


########################################


def extend_hook(cls, priority, **kwargs):
    """
    Decorator that can be attached to a function or a method to make
    a hook out of it. The hook will have the given priority and an
    empty argument list.

    All the (key, value) pairs given in kwargs will be set attributes
    of the hook.
    """
    def decorator(f):
        h = Hook(priority, f)
        for k, v in kwargs.iteritems():
            setattr(h, k, v)
        setattr(cls, f.__name__, h)
        return h
    return decorator

