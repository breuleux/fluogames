
from functools import partial
import util

class Hook(partial):
    """
    Hook class

    A Hook object represents a function called with certain arguments
    with a certain priority over other hooks. They must be inserted in
    HookLists.

    Calling a hook does the following operation:
      hook(arg1, arg2, ...) -> hook.function(hook.arguments + (arg1, arg2, ...))
    """

    def __new__(cls, priority, function, *args, **kwargs):
        """
        Creates a Hook with the given:
          priority: some comparable object. only used if you place the
                    hook in a HookList.
          function: can be any callable
                    if the given argument for function is not a callable,
                    it will be wrapped to a function which always returns
                    that argument (a constant of sorts)
          args:     arguments that will be passed to function
                    when this hook is called

        Examples:
          h1 = Hook(0.0, lambda a, b: a + b, (1, 4))
          h1() # 5
          h2 = Hook(0.0, 27, ())
          h2() # 27
          h3 = Hook(7.2, lambda a, b, c: a + b + c, (1, 4))
          h3(8) # 13
        """
        if not callable(function):
            function = util.always(function)
        self = partial.__new__(cls, function, *args, **kwargs)
        self.priority = priority
        return self

    def specialize(self, *args, **kwargs):
        return self.__class__(self.priority,
                              self.func,
                              *(self.args + args),
                              **dict(self.keywords, **kwargs))

    def __eq__(self, other):
        return other is self or \
            type(self) == type(other) and \
            other.priority == self.priority and \
            other.func == self.func and \
            other.args == self.args

    def __ne__(self, other):
        return not self == other
    
    def __hash__(self):
        return NotImplemented

    def __gt__(self, other):
        return self.priority > other.priority

    def __lt__(self, other):
        return self.priority < other.priority

    def __str__(self):
        return "(p%s: %s%s)" % (self.priority, self.func, self.args)


    

class HookList(object):
    """
    Represents a list of Hook objects, ordered by priority.

    The HookList class provides utilities to add and remove
    hooks in the list:

      add_hook(hook): adds the hook to the list at the place
                      corresponding to its advertised priority

      add_hooks(*hooks): adds several hooks at the same time

      remove_hook(hook): remove the specified hook from the list


    HookList also provides utilities to call the hooks
    in the list:

      collect(*args): generator that yields hook(*args) for
                      each hook in the list

      execute(*args): calls hook(*args) for each hook in the
                      list
    """

    def __init__(self, hooks = []):
        self.hooks = []
        self.used = False
        self.add_hooks(*hooks)

    def __insertion_index__(self, hook):
        # Helper function for binary search
        l = 0
        h = len(self)
        while l < h:
            m = (l+h)/2
            if hook < self.hooks[m]:
                h = m
            else:
                l = m+1
        return l

    def add_hook(self, hook):
        """
        Add a hook to the HookList, such that all the hooks in the
        list are sorted by priority.
        """
        if self.used:
            self.hooks = list(self.hooks)
            self.used = False
        self.hooks.insert(self.__insertion_index__(hook), hook)

    def add_hooks(self, *hooks):
        """
        Adds several hooks at once.
        """
        # This could be made smarter if needed.
        for hook in hooks:
            self.add_hook(hook)
        
    def remove_hook(self, hook):
        """
        Remove the hook from this HookList.
        """
        if self.used:
            self.hooks = [h for h in self.hooks if h != hook]
            self.used = False
            return
        self.hooks.remove(hook)
#         index = self.__insertion_index__(hook) - 1
#         sz = len(self)
#         cursor = index
#         while cursor < sz:
#             hook2 = self[cursor]
#             if hook < hook2:
#                 break
#             elif hook2 != hook:
#                 cursor += 1
#                 continue
#             if not self.iterating:
#                 del self[cursor]
#             else:
#                 self.removals.append(cursor)
#             return
#         cursor = index - 1
#         while cursor >= 0:
#             hook2 = self[cursor]
#             if hook > hook2:
#                 raise ValueError("%s not found in HookList" % hook)
#             elif hook2 != hook:
#                 cursor -= 1
#                 continue
#             if not self.iterating:
#                 del self[cursor]
#             else:
#                 self.removals.append(cursor)
#             return
#         raise ValueError("%s not found in HookList" % hook)

    def remove_hooks(self, *hooks):
        """
        Removes several hooks at once.
        """
        # This could be made smarter if needed.
        for hook in hooks:
            self.remove_hook(hook)

    def check(self):
        """
        Checks that the list is sorted properly.

        Note: this is a debugging interface, HookList does not use this internally.
        """
        def helper(h1, h2):
            if h1 > h2:
                raise AssertionError("HookList is not ordered properly.", self)
            return h2
        reduce(helper, self.hooks)
        return True

    def collect(self, *args):
        """
        Generator which yields hook(*args) for each hook in the list,
        in order of priority. You can break from the generator anytime
        if you don't need to call the remaining hooks.
        """
        self.used = True
        for hook in self.hooks:
            yield hook(*args)
        self.used = False
        #return (hook(*args) for hook in self.hooks)

    def execute(self, *args):
        """
        Calls all hooks in the list in order of priority.
        """
        self.used = True
        for hook in self.hooks:
            hook(*args)
        self.used = False

    __call__ = execute

    def __len__(self):
        return len(self.hooks)

    def __str__(self):
        return str(self.hooks)



def hook(priority, **kwargs):
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
        return h
    return decorator



def reflective_hook(priority, **kwargs):
    """
    Decorator that can be attached to a function or a method to make
    a hook out of it. The hook will have the given priority and an
    argument list which contains one element, the hook itself.

    All the (key, value) pairs given in kwargs will be set attributes
    of the hook.
    """
    def decorator(f):
        h = Hook(priority, f)
        h.arguments = (h,)
        for k, v in kwargs.iteritems():
            setattr(h, k, v)
        return h
    return decorator


class MetaHook(HookList):
    """
    Special kind of hook which is also a HookList. Calling it has
    the effect of calling the hook with the hightest priority and
    not the others. Can be used to override the behavior of a hook
    dynamically.

    Unlike normal hooks, metahook1 == metahook2 -> metahook1 is metahook2
    """

    def __init__(self, priority, init_hook = None):
        self.priority = priority
        if init_hook is not None:
            self.add_hook(init_hook)

    def __gt__(self, other):
        return self.priority > other.priority

    def __lt__(self, other):
        return self.priority < other.priority
    
    def __call__(self, *args):
        """
        Only calls the hook with highest priority.
        """
        return self[0](*args)

    def __str__(self):
        return str(self[0])

