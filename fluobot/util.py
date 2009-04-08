from __future__ import with_statement

import inspect
import re
import os


class inphase(object):

    def __init__(self, obj, phase):
        self.obj = obj
        self.phase = phase
    
    def __enter__(self):
        self.curphase = self.obj.__class__
        phase = self.obj.__phases__()[self.phase] \
            if isinstance(self.phase, str) \
            else self.phase
        self.obj.switch(phase, switch_in = False, switch_out = False)

    def __exit__(self, type, value, traceback):
        self.obj.switch(self.curphase, switch_in = False, switch_out = False)


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


def format(message, bold = False, underline = False, fg = False, bg = False, color = False):
    if isinstance(message, (list, tuple)):
        return [format(m, bold, underline, fg, bg) for m in message]
    color = str(fg) if fg is not False else ''
    if bg is not False: color += ',%s' % bg
    if bold:
        message = '$B%s$B' % message
    if underline:
        message = '$U%s$U' % message
    if color != '':
        message = '$C%s$X%s$C' % (color, message)
    message = message.replace('$B', '\002')
    message = message.replace('$C', '\003')
    message = message.replace('$U', '\037')
    message = message.replace('$X', '\002\002')
    return message

def bold(message):
    return format(message, bold = True)

def underline(message):
    return format(message, underline = True)

def strip(message):
    message = message.split('\n')
    return '\n'.join(map(str.strip, message))

def blockify(message):
    if not message:
        return ""
    rval = []
    rval.append('')
    for line in strip(message).split('\n'):
        if not line:
            if rval and rval[-1]:
                rval.append('')
        else:
            if rval[-1]:
                rval[-1] += ' ' + line
            else:
                rval[-1] = line
    return '\n'.join(rval).strip()

def prepjoin(l, prep = 'and', sep = ', '):
    if not l:
        return ""
    elif len(l) == 1:
        return l[0]
    else:
        return "%s %s %s" % (sep.join(l[:-1]), prep, l[-1])

def filter_command(s, prefixes):
    prefixes = prefixes.split(' ')
    for prefix in prefixes:
        if s.startswith(prefix):
            return s[len(prefix):]
    return None

def parse(message):
    message = message.split()
    def convert(s):
        for fn in (int, float):
            try:
                return fn(s)
            except:
                pass
        return s
    return map(convert, message)


class Info(object):
    
    def __init__(self, bot, user, channel):
        self.bot = bot
        self.raw_user = user
        attempt = user.split('!', 1)
        self.user, self.host = attempt if len(attempt) == 2 else (None, None)
        self.channel = channel
        if self.channel.startswith('#'):
            self.public = True
            self.private = False
        else:
            self.public = False
            self.private = True

    def reply(self, message, modality = None, bold = False, underline = False, fg = False, bg = False):
#         if modality == 'public' or modality is None and self.public:
#             self.bot.broadcast(message, bold, underline, fg, bg)
#         else:
        self.bot.notice(self.user, message, bold, underline, fg, bg)

    def clearance(self):
        try:
            return self.manager.get_plugin('auth').clearance(self.user)
        except KeyError:
            return 0


def require_private(f):
    def newf(info, *args, **kwargs):
        if not info.private:
            raise UsageError('You must do this action in $Bprivate$B.')
        return f(info, *args, **kwargs)
    newf.__doc__ = f.__doc__
    newf.restrictions = list(getattr(f, 'restrictions', []))
    newf.restrictions.append('must be done in $Bprivate$B')
    return newf

def require_public(f):
    def newf(info, *args, **kwargs):
        if not info.public:
            raise UsageError('You must do this action in $Bpublic$B.')
        return f(info, *args, **kwargs)
    newf.__doc__ = f.__doc__
    newf.restrictions = list(getattr(f, 'restrictions', []))
    newf.restrictions.append('must be done in $Bpublic$B')
    return newf

def restrict(n):
    def deco(f):
        def newf(info, *args, **kwargs):
            i = info.clearance()
            if i < n:
                raise UsageError('You do not have the permission to use this command (your level: %s; required level: %s).' % (i, n))
            return f(info, *args, **kwargs)
        newf.__doc__ = f.__doc__
        newf.restrictions = list(getattr(f, 'restrictions', []))
        newf.restrictions.append('requires clearance $B>= %s$B' % n)
        return newf
    return deco
        
    
# def require_private(f):
#     f.require_private = True
#     return f

# def require_public(f):
#     f.require_public = True
#     return f

# def restrict(n):
#     def deco(f):
#         f.clearance = n
#         return f
#     return deco

# def requirement_check(fn, info, reply = False):
#     if getattr(fn, 'require_private', False) and info.public:
#         if reply: info.reply('You must do this action in private.')
#     elif getattr(fn, 'require_public', False) and info.private:
#         if reply: info.reply('You must do this action in public.')
#     elif getattr(fn, 'clearance', False) and info.clearance() < fn.clearance:
#         if reply: info.reply('You do not have the permission to use this command.')
#     else:
#         return True
#     return False


def parent_function():
    return inspect.stack()[2]

def get_help_for(name, x, *subtopics):
    if hasattr(x, 'help'):
        answer = x.help(*subtopics)
    elif subtopics:
        answer = ["There are no subtopics for %s." % name]
    elif x.__doc__:
        answer = [blockify(x.__doc__)]
    else:
        answer = ["There is no documentation for %s." % name]
#     rpub = getattr(x, 'require_public', False)
#     rpriv = getattr(x, 'require_private', False)
#     rclear = getattr(x, 'clearance', 0)
#     if rpub or rpriv or rclear:
#         restrictions = []
#         if rpub: restrictions.append('must be done in $Bpublic$B')
#         if rpriv: restrictions.append('must be done in $Bprivate$B')
#         if rclear: restrictions.append('requires clearance $B>=%s$B' % rclear)
    restrictions = getattr(x, 'restrictions', None)
    if restrictions:
        answer.append("This command %s." % prepjoin(restrictions))
    return answer


class AbortError(Exception):
    pass

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



class Plugin(Stateful):
    
    catch_all_private = False

    @classmethod
    def __phases__(cls):
        return dict(normal = cls)

    @classmethod
    def __invphases__(cls):
        return dict((b, a) for a, b in cls.__phases__().iteritems())

    def __init__(self, name, bot, loc):
        self.name = name
        self.bot = bot
        self.loc = loc

    def broadcast(self, message, bold = False, underline = False, fg = False, bg = False):
        self.bot.broadcast(message, bold, underline, fg, bg)

    def msg(self, user, message, bold = False, underline = False, fg = False, bg = False):
        self.bot.msg(user, message, bold, underline, fg, bg)

    def notice(self, user, message, bold = False, underline = False, fg = False, bg = False):
        self.bot.notice(user, message, bold, underline, fg, bg)

    def get_commands(self):
        raise NotImplementedError("Override get_commands")

    def get_command(self, command):
        raise NotImplementedError("Override get_command")
    
    def do_command(self, info, command, args):
        if isinstance(command, str):
            fn = self.get_command(command)
        else:
            fn = command
            command = getattr(fn, 'name', getattr(fn, '__name__', '???'))

        if fn is None:
            return False
        
        try:
            fn(info, *args)
        except UsageError, e:
            info.reply(e.message
                       or blockify(fn.__doc__).split('\n')[0] # first line of fn.__doc__
                       or 'There was an error executing %s' % command)
        except TypeError, e:
            if typeerror_regexp.match(e.message):
                line1 = blockify(fn.__doc__).split('\n')[0]
                info.reply(line1.startswith('Usage:') and line1
                           or 'There was an error in the number of arguments while executing %s' % command)
            else:
                raise
        return True

    def privmsg(self, info, message):
        raise NotImplementedError("Override privmsg")

    def exec_in_phase(self, phase, fn_name, *args):
        curcls = self.__class__
        self.switch(self.__phases__()[phase], switch_in = False, switch_out = False)
        try:
            rval = getattr(self, fn_name)(*args)
        except:
            raise
        finally:
            self.switch(curcls, switch_in = False, switch_out = False)
        return rval
    
    def phasemap(self, fn_name, *args):
        return dict((cls, self.exec_in_phase(phase, fn_name, *args))
                    for phase, cls in self.__phases__().iteritems())


    
class StandardPlugin(Plugin):

    
    def get_commands(self):
        return dict((x[8:], getattr(self, 'command_' + x[8:]))
                    for x in dir(self) if x.startswith('command_'))

    def get_command(self, command):
        if not isinstance(command, str):
            return None
        fn = getattr(self, 'command_' + command, None)
        return fn

    
    def privmsg(self, info, message):
        orig = message
        message = filter_command(message,
                                 self.bot.conf['public_prefix' if info.public
                                               else 'private_prefix'])
        if message: 
            message = parse(message)
            command, args = message[0], message[1:]
            if self.do_command(info, command, args):
                return
           
#         if info.public and message.startswith(self.bot.conf['command_prefix']):
#             message = parse(message)
#             command, args = message[0][1:], message[1:]
#             if self.do_command(info, command, args):
#                 return
#         elif info.private:
#             message = parse(message)
#             command, args = message[0], message[1:]
#             if self.do_command(info, command, args):
#                 return
        self.privmsg_rest(info, orig)
        
    def privmsg_rest(self, info, message):
        pass

    
    def help(self, *topics):
        
        if not topics:
            doc = self.__doc__ and blockify(self.__doc__) or ""
            #return [doc, 'For a complete list of commands, use $Bhelp commands$B.']
            return [doc] + self.help('commands')

        elif len(topics) == 1 and topics[0] == 'phases':
            phased = self.__phases__()
            phases = phased.keys()
            phases.sort()
            def colorize(x):
                if phased[x] is self.__class__:
                    return format(x, bold = True, fg = 3) + " (current)"
                else:
                    return format(x, bold = False, fg = 4)
            return [format('Phase list', bold = True, underline = False) + ': '
                    + ', '.join(map(colorize, phases))]
        
        elif len(topics) == 1 and topics[0] == 'just_commands':
            all_commands = self.phasemap('get_commands')
            available_commands = set(all_commands.pop(self.__class__).keys())
            commands = list(reduce(lambda x, y: x.union(y.keys()), all_commands.values(), available_commands))
            commands.sort()
            def colorize(x):
                if x in available_commands:
                    return format(x, bold = True, fg = 3)
                else:
                    return format(x, bold = False, fg = 4)
            return [format('Command list', bold = True, underline = False) + ': '
                    + ', '.join(map(colorize, commands))]

        elif len(topics) == 1 and topics[0] == 'commands':
            if len(self.__phases__()) > 1:
                return self.help('phases') + self.help('just_commands')
            else:
                return self.help('just_commands')

        elif topics[0] in self.__phases__():
            curcls = self.__class__
            #message = self.exec_in_phase(topics[0], 'help', *topics[1:])
            with inphase(self, topics[0]):
                message = self.help(*topics[1:])
            return message

        else:
            main, subtopics = topics[0], topics[1:]
            candidates = self.phasemap('get_command', main)

            command = candidates.pop(self.__class__)
            if command:
                answer = [get_help_for(main, command, *subtopics)]
            else:
                answer = []

            for phase, command in candidates.iteritems():
                if command:
                    text = get_help_for(main, command, *subtopics)
                    if text not in answer:
                        answer.append('Command available in $B%s$B phase:' % self.__invphases__()[phase])
                        answer.append(text)

            if not answer:
                raise UsageError('No such command: %s' % bold(main))

            return answer


    def command_help(self, info, *topics):
        """
        Usage: $Bhelp <topic> [<subtopic1> <subtopic2> ...]$B

        Provides help about the topic specified.
        """
        help = self.help(*topics)
        info.reply(help)


    def tick(self):
        pass

    def tick10(self):
        pass



class ManagedPlugin(StandardPlugin):

    def __init__(self, manager, name, loc):
        super(ManagedPlugin, self).__init__(name, manager.bot, loc)
        self.manager = manager
        self._orig_phase = self.__class__

    def reset(self):
        self.switch(self._orig_phase)
        
    def __call__(self, info, cmd, *args):
        """
        Usage: $Bmain command arg1 arg2 ...$B
        """
        self.do_command(info, cmd, args)



class ScheduledPlugin(ManagedPlugin):

    def schedule(self, timeouts, switch_to):
        self.timeouts = list(timeouts)
        self.switch_to = switch_to

    def timeout(self, *timeouts):
        self.schedule(timeouts, None)

    def remaining(self):
        return sum(self.timeouts)
        
    def tick(self):
        if not hasattr(self, 'timeouts') or not self.timeouts:
            return
        self.timeouts[0] -= 1
        if self.timeouts[0] == 0:
            self.timeouts[:1] = []
            if not self.timeouts:
                if not self.switch_to:
                    self.broadcast('Time out!')
                    self.manager.abort()
                else:
                    self.switch(self.switch_to)
            else:
                self.broadcast('%i seconds remaining!' % self.remaining())

