
import inspect
import re


def wrap_msg(message, color = False, bold = False, underline = False):
    if bold:
        message = '$B%s$B' % message
    if underline:
        message = '$U%s$U' % message
    if color is not False:
        message = '$C$B$B$i%s$C' % (color, message)
    return message

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
    def respond(self, message, modality = None):
        if modality == 'public' or modality is None and self.public:
            self.bot.broadcast(message)
        else:
            self.bot.notice(self.user, message)

def require_private(f):
    f.require_private = True
    return f

def require_public(f):
    f.require_public = True
    return f

def parent_function():
    return inspect.stack()[2]


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

    def __init__(self, bot):
        self.bot = bot

    def broadcast(self, message, color = False, bold = False, underline = False):
        self.bot.broadcast(message, color, bold, underline)

    def msg(self, user, message, color = False, bold = False, underline = False):
        self.bot.msg(user, message, color, bold, underline)

    def notice(self, user, message, color = False, bold = False, underline = False):
        self.bot.notice(user, message, color, bold, underline)

    def do_command(self, info, command, args):
        fn = getattr(self, command, None)
        if fn is not None:
            if getattr(fn, 'require_private', False) and info.public \
                    or getattr(fn, 'require_public', False) and info.private:
                pass
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
            command, args = 'command_%s' % message[0][1:], message[1:]
            if self.do_command(info, command, args):
                return
        elif info.private:
            message = parse(message)
            command, args = 'command_%s' % message[0], message[1:]
            if self.do_command(info, command, args):
                return
        self.privmsg_rest(info, orig)
