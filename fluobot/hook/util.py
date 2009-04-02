
import math

def product(seq, init=1):
    for x in seq:
        init *= x
        if init == 0:
            return init
    return init

def floor_product(seq, init=1):
    for x in seq:
        init = int(init * x)
        if init == 0:
            return init
    return init

def round_product(seq, init=1):
    for x in seq:
        init = math.round(init * x)
        if init == 0:
            return init
    return init

def always(v):
    """
    always(v) ->
    Returns a function that returns v regardless of its arguments.
    """
    def f(*_, **__):
        return v
    return f
