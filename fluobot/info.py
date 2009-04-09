

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
        self.bot.notice(self.user, message, bold, underline, fg, bg)

    def clearance(self):
        try:
            return self.bot.manager.get_plugin('auth').clearance(self.user)
        except KeyError:
            return 0

