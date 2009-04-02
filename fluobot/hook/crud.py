
# was in metaclass ExtensibleMC __new__
#         __orig_init__ = getattr(cls, '__init__', None)
#         def __wrap_init__(self, *args, **kwargs):
#             print args, kwargs
#             for extender in cls.__extenders__:
#                 extender.apply_to_instance(self)
#             if __orig_init__:
#                 __orig_init__(self, *args, **kwargs)

#         cls.__init__ = __wrap_init__
#         return cls



# class Extensible(object):

#     # @todo: use a metaclass to speed up the work (find the wrappers, filter out
#     # elements from the __dict__ that can't be wrapped)

#     def __wrap_hook__(self, name, hook):
#         if isinstance(hook, Hook):
#             return hook.specialize(self)

#     def __wrap_hooklist__(self, name, hooklist):
#         if isinstance(hooklist, HookList):
#             return hooklist.__class__([h.specialize(self) for h in hooklist])
    
#     def __new__(cls, *args, **kwargs):
#         self = object.__new__(cls, *args, **kwargs)
#         self.__pre_init__()
#         wrappers = [getattr(self, name) for name in dir(cls) if name.startswith("__wrap")]
#         for attr, value in cls.__dict__.iteritems():
#             for wrapper in wrappers:
#                 new_value = wrapper(attr, value)
#                 if new_value is not None:
#                     setattr(self, attr, new_value)
#         return self

#     def __pre_init__(self):
#         pass





# class Confusion(HolderAction):

#     @hook(0.0)
#     def decrease_counter(self):
#         self.value -= 1
#         if self.value == 0:
#             self.game.say("%s is not confused anymore >:)" % self.holder)

#     @hook(0.0)
#     def action_filter(self):
#         if self.game.random() < 0.5:
#             self.holder.take_damage(whatever)
#             self.game.say("%s hurt itself in confusion!" % self.holder)
#             return False
#         return True

#     def hook_map(self):
#         return {self.holder.before_move: self.decrease_counter,
#                 self.holder.can_move: self.action_filter}


# Slot.add_counter('confused', Confusion)



# class Paralyzed(HolderAction):
#     @hook(0.0)
#     def paralysis(self):
#         if self.game.random() < 0.25:
#             self.game.say("%s is fully paralyzed!" % self.holder)
#             return False
#         else:
#             return True

#     @hook(0.0)
#     def speed_cut(self):
#         return 0.25

#     def hook_map(self):
#         return {self.holder.can_move: self.paralysis,
#                 self.holder.speed_modifiers: self.speed_cut}

# ...

# Slot.add_enum('status',
#               PAR = Paralyzed,
#               PSN = Poison,
#               ...)







# class PursuitAction(Action):

#     def __init__(self, act_normal, act_switch):
#         self.act_normal = act_normal
#         self.act_switch = act_switch

#     def instantiate(self, user, target):
#         c = copy(self)
#         c.user = user
#         c.target = target
#         c.game = c.user.game
#         return c
        
#     def normal(self):
#         self.act_normal(self.user)

#     def on_switch(self):
#         self.act_switch(self.user)
#         self.uninstall('normal')

#     def hook_map(self):
#         return dict(normal = (self.game.moves, Hook(self.user.speed, self.normal, self)),
#                     switch = (self.target.on_switch_out, Hook(0.0, self.on_switch, self)),
#                     remove = (self.game.cleanup_turn, Hook(0.0, self.uninstall, 'normal', 'switch')))







class Test(Extensible):
    def __init__(self):
        self.message = "YEAH"

@extend(Test)
def f(self):
    print "hi buddy"
    print self.message

@extend(Test)
def g(self, x):
    print x + 6

@extend_hook(Test, 0.2)
def h(self, x):
    return x + 6

Test.hookity = HookList()
Test.hookity.add_hook(Hook(0.0, lambda self: "Grotesque%s" % self))


# @flag(Test)
# def mean_look(self):
#     @hook(0.0)
#     def prevent_switching(action_list):
#         return [a for a in action_list if not isinstance(a, SwitchAction)]
#     self.action_filters.add_hook(prevent_switching)


# @enum(Test)
# def status():
#     def poison(self):
#         pass
#     def paralysis(self):
#         pass


t = Test()
t.f()
t.g(21)
print t.h
print t.h.priority, t.h.func, t.h.args
print t.h(44)
print list(t.hookity.collect())


# class ExtensibleMC(type):
    
#     def __new__(mcls, name, bases, dct):
#         cls = type.__new__(mcls, name, bases, dct)
# #        print dir(cls)
# #        super(type, cls).__init__(name, bases, dct)
#         cls.__ext_hooks__ = {}
#         cls.__ext_hooklists__ = {}

#         print "A", dir(cls)
#         for attr, value in dct.iteritems():
#             # Technically, the attributes are already all in the class
#             # but __setattr__ has additional behavior
#             setattr(cls, attr, value)
#         print "B", dir(cls)
        
# #         __init__ = dct.get('__init__', None)
# #         def __new_init__(self, *args, **kwargs):
# #             for name, hook in cls.__ext_hooks__.iteritems():
# #                 setattr(self, name, hook.specialize(self)) # Hook(hook.priority, hook.func, (self,) + hook.args))
# #             for name, hooklist in cls.__ext_hooklists__.iteritems():
# #                 hooklist = copy(hooklist)
# #                 hooklist[:] = [h.specialize(self) for h in hooklist]
# #                 setattr(self, name, hooklist)
# #             if __init__:
# #                 __init__(self, *args, **kwargs)
#         #setattr(cls, '__orig_init__' getattr(cls, '__init__', None))
#         setattr(cls, '__init__', __new_init__)
#         return cls

#     def __wrap_init__(cls, self, *args, **kwargs):
#         for name, hook in cls.__ext_hooks__.iteritems():
#             setattr(self, name, hook.specialize(self)) # Hook(hook.priority, hook.func, (self,) + hook.args))
#         for name, hooklist in cls.__ext_hooklists__.iteritems():
#             hooklist = copy(hooklist)
#             hooklist[:] = [h.specialize(self) for h in hooklist]
#             setattr(self, name, hooklist)
#         if cls.__orig_init__:
#             cls.__orig_init__(self, *args, **kwargs)

#     def __reg_hook__(cls, name, hook):
#         cls.__ext_hooks__[name] = hook

#     def __reg_hooklist__(cls, name, hooklist):
#         cls.__ext_hooklists__[name] = hooklist

#     def __setattr__(cls, attr, value):
#         print attr, value
#         if isinstance(value, Hook):
#             cls.__reg_hook__(attr, value)
#         elif isinstance(value, HookList):
#             cls.__reg_hooklist__(attr, value)
#         type.__setattr__(cls, attr, value)















# class Counter(object):

#     def __init__(self, owner, action_class):
#         self._value = value
#         self.action = action_class(owner)
#         self.action.control = self

#     def get(self):
#         return self._value

#     def set(self, value):
#         if self._value == 0 and value > 0:
#             self.action.install()
#         elif self._value != 0 and value == 0:
#             self.action.uninstall()
#         self._value = value

#     value = property(get, set)


# def counter(action_class):
#     return Property(partial(Counter, action_class = action_class))



# class MetaProperty(object):

#     def __init__(self, name, factory):
#         self.name = "_" + name
#         self.factory = factory

#     def __getprop__(self, obj):
#         prop = getattr(obj, self.name, None)
#         if prop is None:
#             prop = self.factory(obj)
#             setattr(obj, name, prop)
#         return prop
        
#     def __get__(self, obj):
#         return self.__getprop__(obj).get()

#     def __set__(self, obj, value):
#         self.__getprop__(obj).set(value)


# class Property(object):

#     def __init__(self, owner, value):
#         self.owner = owner
#         self.value = value

#     def set(self, value):
#         self.value = value

#     def get(self):
#         return self.value


















# class TestPokemon(Extensible):

#     woo = hooks.HookList()
#     yea = hooks.HookList()


#     def __init__(self, message):
#         self.message = message
    
#     def test(self):
#         self.woo.execute()
#         self.yea.execute()


# class TestCounter(OwnerAction, Counter):

#     @autohook(0.1)
#     def woo(self):
#         print self.value, self.owner.message

#     @autohook(0.2)
#     def yea(self):
#         self.counter -= 1
#         print "counter--", self.value

# TestPokemon.c = Property(TestCounter)

# t = TestPokemon("hello there")
# t.test()
# t.c = 4
# for i in xrange(10):
#     print i
#     t.test()



class A1(OwnerAction):
    @autohook(0)
    def woo(self):
        print "A1"

class A2(OwnerAction):
    @autohook(0)
    def woo(self):
        print "A2"

class A3(OwnerAction):
    @autohook(0)
    def woo(self):
        print "A3"

TestPokemon.e = enum(a1 = A1,
                     a2 = A2,
                     a3 = A3)

t = TestPokemon("hello there")
t.test()
t.e = "a1"
t.test()
t.test()
t.e = "a2"
t.test()
t.e = "a3"
t.test()
print t.e
t.e = None
print t.e
t.test()

















# class Test(Extensible):
#     def __init__(self):
#         self.message = "YEAH"
        
# @extend(Test)
# def f(self):
#     print "hi buddy"
#     print self.message

# @extend(Test)
# def g(self, x):
#     print x + 6

# @extend_hook(Test, 0.2)
# def h(self, x):
#     return x + 6

# Test.hookity = HookList()
# Test.hookity.add_hook(Hook(0.0, lambda self: "Grotesque%s" % self))


# t = Test()
# t.f()
# t.g(21)
# #print t.h.priority, t.h.func, t.h.args
# print t.h(44)
# print list(t.hookity.collect())


# class Tata:
#     def __init__(self, obj):
#         self.x = 0.33
#         self.obj = obj
#     def get(self):
#         return self.x
#     def set(self, x):
#         self.x = x
#     value = property(get, set)



# class Test2(Test):
#     def __init__(self):
#         self.message = "YEAH2"
#     @hook(0.22)
#     def woopah(self):
#         return self.message
#     pop = Property(Tata)

# @extend_hook(Test2, 0.3)
# def h(self, x):
#     return x + 7


# t = Test()
# t2 = Test2()
# t2.f()
# #print t2.h2(44)
# print t2.h(44)
# print t.h(44)
# print t2.woopah()

# print t2.pop
# print t2._pop.get()
# t2.pop = "gotcha"
# print t2.pop



########################################

class Value(object):
    def __init__(self, v):
        self.value = v

class ValueExtender(Extender):
    def register(self, name, prop):
        if not isinstance(prop, Value):
            raise TypeError
        self.__registry__[name] = prop
        return {name: prop}
    def apply_to_instance(self, instance):
        for name, value in self.__registry__.iteritems():
            setattr(instance, name, copy(value.value))
