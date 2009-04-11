
from __future__ import with_statement

import util
from util import Stateful, UsageError
from format import *


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


def autoparse(f):
    def newf(self, info, *args):
        args = parse(args)
        return f(self, info, *args)
    return newf

def require_private(f):
    def newf(self, info, *args, **kwargs):
        if not info.private:
            raise UsageError('You must do this action in $Bprivate$B.')
        return f(self, info, *args, **kwargs)
    newf.__doc__ = f.__doc__
    newf.restrictions = list(getattr(f, 'restrictions', []))
    newf.restrictions.append('must be done in $Bprivate$B')
    return newf

def require_public(f):
    def newf(self, info, *args, **kwargs):
        if not info.public:
            raise UsageError('You must do this action in $Bpublic$B.')
        return f(self, info, *args, **kwargs)
    newf.__doc__ = f.__doc__
    newf.restrictions = list(getattr(f, 'restrictions', []))
    newf.restrictions.append('must be done in $Bpublic$B')
    return newf

def restrict(n):
    def deco(f):
        def newf(self, info, *args, **kwargs):
            i = info.user.clearance
            if i < n:
                raise UsageError('You do not have the permission to use this command (your level: %s; required level: %s).' % (i, n))
            return f(self, info, *args, **kwargs)
        newf.__doc__ = f.__doc__
        newf.restrictions = list(getattr(f, 'restrictions', []))
        newf.restrictions.append('requires clearance $B>= %s$B' % n)
        return newf
    return deco



def get_help_for(name, x, *subtopics):
    if hasattr(x, 'help'):
        answer = x.help(*subtopics)
    elif subtopics:
        answer = ["There are no subtopics for %s." % name]
    elif x.__doc__:
        answer = [blockify(x.__doc__)]
    else:
        answer = ["There is no documentation for %s." % name]
    restrictions = getattr(x, 'restrictions', None)
    if restrictions:
        answer.append("This command %s." % prepjoin(restrictions))
    return answer


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
            if util.typeerror_regexp.match(e.message):
                line1 = blockify(fn.__doc__).split('\n')[0]
                info.reply(line1.startswith('Usage:') and line1
                           or 'There was an error in the number of arguments while executing %s' % command)
            else:
                raise
        return True

    def on_privmsg(self, info, message):
        raise NotImplementedError("Override on_privmsg")

    def watch(self, info, message):
        pass

    def on_join(self, info):
        pass

    def on_nick_change(self, oldnick, newnick):
        pass

    def on_kick(self, kicker_info, kicked_nick, message):
        pass

    def on_part(self, info, message):
        pass

    def on_quit(self, quitter, message):
        pass

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

    
    def on_privmsg(self, info, message):
        orig = message
        message = filter_command(message,
                                 self.bot.conf['public_prefix' if info.public
                                               else 'private_prefix'])
        if message:
            message = message.split() #parse(message)
            command, args = message[0], message[1:]
            if self.do_command(info, command, args):
                return
        self.on_privmsg_rest(info, orig)
        
    def on_privmsg_rest(self, info, message):
        pass

    
    def help(self, *topics):
        
        if not topics:
            doc = self.__doc__ and blockify(self.__doc__) or ""
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
        self.setup()

    def setup(self):
        pass
    
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

