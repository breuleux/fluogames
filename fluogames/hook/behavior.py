
import hooks
from class_tools import Extender, Extensible, Property
from functools import partial


class Behavior(Extensible):
    """
    An Behavior is an object representing a group of hooks that can be
    installed or uninstalled at once on a group of hooklists.
    """

    def installed(self):
        """
        Returns True if this Behavior is installed. Else, returns False.
        """
        raise NotImplementedError
    
    def install(self):
        """
        Install all the hooks associated to this Behavior on their
        corresponding HookLists.

        If the Behavior was already installed, does nothing and returns
        False. Else, returns True.
        """
        raise NotImplementedError

    def uninstall(self):
        """
        Uninstall the hooks installed by a previous call to install().

        If the Behavior was not installed, does nothing and return False.
        Else, returns True.
        """
        raise NotImplementedError


class MappedBehavior(Behavior):
    """
    A MappedBehavior uses a single method, hook_map() to determine how
    to do the install and the uninstall.
    """

    def installed(self):
        return hasattr(self, "_installed")

    def install(self):
        """
        Installs all the hooks returned by hook_map().

        If the Behavior was already installed, does nothing and returns
        False. Else, returns True.
        """
        if hasattr(self, "_installed"):
            return False
        self._installed = self.hook_map()
        for hl, h in self._installed:
            hl.add_hook(h)
        return True

    def uninstall(self):
        """
        Uninstalls all the hooks returned by hook_map().

        If the Behavior was not installed before, does nothing and returns
        False. Else, returns True.
        """        
        installed = getattr(self, "_installed", None)
        if installed is None:
            return False
        for hl, h in installed:
            hl.remove_hook(h)
        del self._installed
        return True

    def hook_map(self):
        """
        Returns a list of (hooklist, hook) pairs. For each pair, the
        install method will install the specified hook on the
        specified hooklist. This method is called each time install()
        is called and the hooks are installed. The map is cached for
        use with uninstall().
        """
        return []


class AutoHookExtender(Extender):
    def register(self, name, prop):
        print name, prop, type(prop)
        if not isinstance(prop, hooks.Hook):
            raise TypeError
        self.__registry__[name] = prop
        return {name: prop}
    def apply_to_instance(self, instance):
        instance.__auto_hooks__ = []
        for name, hook in self.__registry__.iteritems():
            auto = getattr(hook, 'auto', False)
            hook = hook.specialize(instance)
            setattr(instance, name, hook)
            if auto:
                instance.__auto_hooks__.append((name, hook))


class OwnerBehavior(MappedBehavior):
    """
    Behavior which is associated to an "owner". Any hook defined in an
    OwnerBehavior which has its "auto" field set to True will be an
    "autohook". An autohook named x will be installed on the HookList
    self.owner.x.
    """
    
    __extenders__ = [AutoHookExtender()]

    def __init__(self, owner):
        self.owner = owner
        auto = []
        for name, hook in self.__auto_hooks__:
            auto.append((getattr(owner, name), hook))
        self.__auto_hooks__ = auto

    def install(self):
        if not super(OwnerBehavior, self).install():
            return False
        for hl, h in self.__auto_hooks__:
            hl.add_hook(h)
        return True

    def uninstall(self):
        if not super(OwnerBehavior, self).uninstall():
            return False
        for hl, h in self.__auto_hooks__:
            hl.remove_hook(h)
        return True


autohook = partial(hooks.hook, auto = True)



class Flag(object):
    """
    Mixin for use with a Behavior subclass. Inheriting from Flag gains
    one field, value. Setting value to True installs the Behavior,
    setting it to False uninstalls it.
    """

    def __get(self):
        return self.installed()

    def __set(self):
        current = self.value
        if not current and value:
            self.install()
        elif current and not value:
            self.uninstall()

    value = property(__get, __set)


class Counter(object):
    """
    Mixin for use with a Behavior subclass. Inheriting from Counter
    gains one field, value, serving as a counter. If the counter is 0,
    the Behavior is uninstalled. Else, it is installed. The Behavior's
    hooks may manipulate the counter as they see fit.
    """
    
    def __get(self):
        # The counter is not necessarily accurate if the Behavior was
        # installed/uninstalled directly. If installed directly, the
        # counter is assumed to be 1.
        return getattr(self, '_counter', 1) if self.installed() else 0

    def __set(self, value):
        current = self.value
        if current == 0 and value > 0:
            self.install()
        elif current != 0 and value == 0:
            self.uninstall()
        self._counter = value

    value = property(__get, __set)
    counter = value


class Enum(object):
    """
    Enum takes a 'mapping' as keyword arguments from a string to
    a Behavior class (or a function returning a Behavior). Each class
    in the mapping is instantiated with the rest of the arguments.

    Setting enum.value to a string installs the corresponding Behavior
    in the mapping (and uninstalls the previously installed Behavior, if
    any). Setting enum to None uninstalls the current Behavior.
    """

    def __init__(self, *arguments, **mappings):
        self._value = None
        self.mappings = {}
        for name, cls in mappings.iteritems():
            obj = cls(*arguments)
            obj.id = name
            self.mappings[name] = obj

    def __get(self):
        return self._value and self.mappings[self._value]

    def __set(self, value):
        current = self._value
        if current is not None and current != value:
            self.mappings[current].uninstall()
        if value is not None and value != current:
            self.mappings[value].install()
        self._value = value

    value = property(__get, __set)


def enum(**kwargs):
    return Property(partial(Enum, **kwargs))




def wrap_as(cls, attr, wattr):
    vattr = "validate_" + attr
    battr = "before_" + attr
    aattr = "after_" + attr
    setattr(cls, vattr, HookList())
    setattr(cls, battr, HookList())
    setattr(cls, aattr, HookList())

    def getter(self):
        return getattr(self, attr)
    
    def setter(self, value):
        def g(x): return getattr(self, x)
        current = g(attr)
        if all(g(vattr).collect(current, value)):
            g(battr).execute(current, value)
            setattr(self, attr, value)
            g(aattr).execute(current, value)

    setattr(cls, wattr, property(getter, setter))

