
from .. import hooks as H
import random
import py


def xhook(x):
    # hook with priority x which returns x
    return H.Hook(x, lambda x: x, x)

def advhook(c, nargs, x, y):
    # hook trying to make use of all features of Hook and HookList
    # records its execution in the counter c
    def f(x, y, *rest):
        assert len(rest) == nargs-2
        c.n += 1
        return x + y + sum(rest)
    return H.Hook(x, f, x, y)

class counter:
    def __init__(self):
        self.n = 0

def test_collect_1():
    # tests collect
    hk1 = xhook(2.7)
    hl = H.HookList()
    hl.add_hook(hk1)
    results = list(hl.collect())
    print results
    assert results == [2.7]

def test_collect_2():
    # tests collect again
    c = counter()
    hooks = [advhook(c, 3, x, 2) for x in xrange(10)]
    hl = H.HookList()
    hl.add_hooks(*hooks)
    results = list(hl.collect(100))
    print c.n
    assert c.n == 10
    assert results == [x + 102 for x in xrange(10)]

def test_collect_cutoff():
    # tests collect if we don't request all results
    c = counter()
    hooks = [advhook(c, 3, x, 2) for x in xrange(10)]
    hl = H.HookList()
    hl.add_hooks(*hooks)
    for i, v in enumerate(hl.collect(100)):
        print i, v
        assert v == i + 102
        if i == 4:
            break
    print c.n
    assert c.n == 5

def test_execute():
    # tests execute
    c = counter()
    hooks = [advhook(c, 3, x, 2) for x in xrange(10)]
    hl = H.HookList()
    hl.add_hooks(*hooks)
    hl.execute(100)
    print c.n
    assert c.n == 10

def test_remove():
    # tests remove_hook
    indices = list(xrange(100))
    keep = list(xrange(0, 100, 3))
    hooks = map(xhook, indices)
    hl = H.HookList()
    hl.add_hooks(*hooks)
    for hook in hooks:
        if hook.priority not in keep:
            hl.remove_hook(hook)
    results = list(hl.collect())
    print results
    assert results == keep

# def test_remove_eq():
#     # - tests that __eq__ works to remove hooks
#     # - tests that trying to remove nonexistant hooks raises an exception
#     indices = list(xrange(10))
#     hooks = map(xhook, indices)
#     hl = H.HookList()
#     hl.add_hooks(*hooks)
#     print hl[3]
#     hl.remove_hook(H.Hook(3.0, hl[3].func, *hl[3].args))
#     hl.cleanup()
#     print len(hl)
#     assert len(hl) == 9
# #     py.test.raises(ValueError, hl.remove_hook, H.Hook(-22.7, None)) # before all the others
# #     py.test.raises(ValueError, hl.remove_hook, H.Hook(1.7, None))   # in between
# #     py.test.raises(ValueError, hl.remove_hook, H.Hook(991.7, None)) # after all the others

def test_correct_order():
    # tests that HookList truly sorts by priority
    indices = list(range(100))
    random.shuffle(indices)
    print indices
    hooks = map(xhook, indices)
    hl = H.HookList()
    for hook in hooks:
        hl.add_hook(hook)
    assert hl.check()
    print "collected results: ", list(hl.collect())
    assert list(hl.collect()) == list(range(100))

def test_correct_order_dups():
    # tests that HookList truly sorts by priority,
    # in a situation where some hooks have the same
    # priority.
    indices = map(lambda x: x/2, list(range(200)))
    random.shuffle(indices)
    print indices
    hooks = map(xhook, indices)
    hl = H.HookList()
    for hook in hooks:
        hl.add_hook(hook)
    assert hl.check()
    print "collected results: ", list(hl.collect())
    assert list(hl.collect()) == map(lambda x: x/2, list(range(200)))

