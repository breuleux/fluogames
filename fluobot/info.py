


class User(object):

    def __init__(self, raw_nick):
        if '!' in raw_nick:
            self.nick, self.host = raw_nick.split('!', 1)
        else:
            self.nick, self.host = raw_nick, 'UNKNOWN'

    def __eq__(self, other):
        if isinstance(other, str):
            if other.lower() == self.nick.lower():
                return True
        elif isinstance(other, User):
            return self.nick.lower() == other.nick.lower()
#             return self is other
#             return self.host == other.host \
#                 and self.nick.lower() == other.nick.lower()

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.nick.lower()) # ^ hash(self.host)

    def __add__(self, other):
        return str(self) + other

    def __radd__(self, other):
        return other + str(self)

    def __str__(self):
        return self.nick

    def __len__(self):
        return len(self.nick)
    
    def __repr__(self):
        return '"%s!%s"' % (self.nick, self.host)

    def __cmp__(self, other):
        return cmp(self.nick.lower(), other.nick.lower())
    

class Info(object):
    
    def __init__(self, bot, user, channel):
        self.bot = bot
#         self.raw_user = user
#         attempt = user.split('!', 1)
#         self.user, self.host = attempt if len(attempt) == 2 else (None, None)
        self.user = user
        self.channel = channel
        if self.channel.startswith('#'):
            self.public = True
            self.private = False
        else:
            self.public = False
            self.private = True

    def reply(self, message, modality = None, bold = False, underline = False, fg = False, bg = False):
        self.bot.notice(self.user, message, bold, underline, fg, bg)

#     def clearance(self):
#         try:
#             return self.bot.manager.get_plugin('auth').clearance(self.user)
#         except KeyError:
#             return 0

