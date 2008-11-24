
import inspect
import re


def format(message, bold = False, underline = False, fg = False, bg = False, color = False):
    color = ','.join([str(fg) if fg is not False else '',
                      str(bg) if bg is not False else ''])
    if bold:
        message = '$B%s$B' % message
    if underline:
        message = '$U%s$U' % message
    if color != ',':
        message = '$C%s$X%s$C' % (color, message)
    return message

def bold(message):
    return format(message, bold = True)


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
    def respond(self, message, modality = None, bold = False, underline = False, fg = False, bg = False):
#         if modality == 'public' or modality is None and self.public:
#             self.bot.broadcast(message, bold, underline, fg, bg)
#         else:
        self.bot.notice(self.user, message, bold, underline, fg, bg)
    def clearance(self):
        return max(self.bot.user_status.get(self.user, [0]))

def require_private(f):
    f.require_private = True
    return f

def require_public(f):
    f.require_public = True
    return f

def restrict(n):
    def deco(f):
        f.clearance = n
        return f
    return deco

def parent_function():
    return inspect.stack()[2]


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


class MiniBot(Stateful):

    catch_all_private = False
    flatten_commands = False

    def __init__(self, bot):
        self.bot = bot

    def broadcast(self, message, bold = False, underline = False, fg = False, bg = False):
        self.bot.broadcast(message, bold, underline, fg, bg)

    def msg(self, user, message, bold = False, underline = False, fg = False, bg = False):
        self.bot.msg(user, message, bold, underline, fg, bg)

    def notice(self, user, message, bold = False, underline = False, fg = False, bg = False):
        self.bot.notice(user, message, bold, underline, fg, bg)

    def get_commands(self):
        return [x[8:] for x in dir(self) if x.startswith('command_')]

    def get_command(self, command):
        if not isinstance(command, str):
            return None
        fn = getattr(self, 'command_' + command, None)
        return fn

    def do_command(self, info, command, args):
        fn = self.get_command(command)
        if fn is not None:
            if getattr(fn, 'require_private', False) and info.public:
                info.respond('You must do this action in private.')
            elif getattr(fn, 'require_public', False) and info.private:
                info.respond('You must do this action in public.')
            elif getattr(fn, 'clearance', False) and info.clearance() < fn.clearance:
                info.respond('You do not have the permission to use this command.')
            else:
                try:
                    fn(info, *args)
                except UsageError, e:
                    if not e.message:
                        for x in fn.__doc__.split('\n'):
                            x = x.strip()
                            if x:
                                info.respond(x)
                                break
                    else:
                        info.respond(e.message)
                except TypeError, e:
                    if typeerror_regexp.match(e.message):
                        for x in fn.__doc__.split('\n'):
                            x = x.strip()
                            if x:
                                info.respond(x)
                                break
                    else:
                        raise
            return True
        return False
        
    def privmsg_rest(self, info, message):
        pass
    
    def privmsg(self, info, message):
        orig = message
        if info.public and message.startswith('!'):
            message = parse(message)
            command, args = message[0][1:], message[1:]
            if self.do_command(info, command, args):
                return
        elif info.private:
            message = parse(message)
            command, args = message[0], message[1:]
            if self.do_command(info, command, args):
                return
        self.privmsg_rest(info, orig)

    def help(self, *topics):
        if not topics:
            commands = self.get_commands()
            return [format('Command list:', bold = True, underline = True) + ' '
                    + ', '.join(sorted(map(bold, commands)))]
        else:
            main, topics = topics[0], topics[1:]
            command = self.get_command(main)
            if not command:
                raise UsageError('No such command: %s' % bold(main))
            if not topics:
                if hasattr(command, 'help'):
                    return command.help()
                else:
                    answer = []
                    if command.__doc__:
                        answer.append('')
                        for line in map(str.strip, command.__doc__.split('\n')):
                            if not line:
                                if answer and answer[-1]:
                                    answer.append('')
                            elif answer:
                                if answer[-1]:
                                    answer[-1] += ' ' + line
                                else:
                                    answer[-1] = line
                    if not answer:
                        answer.append('No documentation for %s' % command)
                    return answer
            else:
                if not hasattr(command, 'help'):
                    raise UsageError('Help for %s has no subtopics.' % bold(main))
                return command.help(*topics)
    
    def command_help(self, info, *topics):
        """
        Usage: $Bhelp <topic> [<subtopic1> <subtopic2> ...]$B

        Provides help about the topic specified.
        """
        help = self.help(*topics)
        if isinstance(help, str):
            info.respond(help)
        elif isinstance(help, (list, tuple)):
            map(info.respond, help)
        else:
            raise UsageError("There's a bug in the help implementation. It returns a wrong type.")
        
