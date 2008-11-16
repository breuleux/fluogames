
import util

class Manager(util.MiniBot):

    def __init__(self, bot):
        super(Manager, self).__init__(bot)
        self.registry = {}
        self.game = None
        
    def add_game(self, name, module, symbol):
        module = __import__(module)
        self.registry[name] = (module, symbol)

    def abort(self):
        if self.game:
            self.game.abort()
            self.game = None

    def reload(self):
        self.abort()
        for name, (module, symbol) in self.registry.iteritems():
            self.registry[name] = (reload(module), symbol)

    def privmsg_rest(self, info, message):
        if self.game:
            self.game.privmsg(info, message)
            
    @util.require_public
    def command_play(self, info, name, *args):
        if self.game:
            info.respond('There is already a game of %s going on.' % self.game.name)
        else:
            try:
                module, symbol = self.registry[name]
            except KeyError:
                info.respond('No such game: %s' % name)
            self.game = getattr(module, symbol)(self, name, info.channel, args)
            self.game.start(info)

    @util.require_public
    def command_abort(self, info):
        """
        Usage: $Babort$B

        Aborts the current game.
        """
        if self.game:
            game = self.game
            self.abort()
            info.respond('Game of %s aborted by %s.' % (game.name, info.user))
        else:
            info.respond('No game going on right now.')

    @util.require_public
    def command_reload(self, info):
        """
        Usage: $Breload$B

        Reloads the current game.
        """
        info.respond('Games reloaded by %s.' % info.user)
        self.reload()

    def command_help(self, info, command = None):
        """
        Usage: $Bhelp <command>$B

        Provides help about the command.
        """
        if command is None:
            general = [x[8:] for x in dir(self) if x.startswith('command_')]
            info.respond('$B$UGeneral commands:$U %s$B' % ', '.join(general))
            if self.game:
                game = [x[8:] for x in dir(self.game) if x.startswith('command_')]
                info.respond('$B$U%s commands:$U %s$B' % (self.game.name, ', '.join(game)))
            return
        
        answer = []
        cname = 'command_%s' % command
        fn = getattr(self, cname, None)
        if not fn and self.game:
            fn = getattr(self.game, cname, None)
        if not fn:
            answer.append('Unknown command: %s' % command)
        else:
            answer.append('')
            for line in map(str.strip, fn.__doc__.split('\n')):
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
        map(info.respond, answer)

#         if info.private:
#             for line in answer:
#                 self.notice(info.user, line)
#         else:
#             map(self.broadcast, answer)


