
import util

class Manager(util.MiniBot):

    def __init__(self, bot, db_dir):
        super(Manager, self).__init__(bot)
        self.registry = {}
        self.game = None
        self.db_dir = db_dir

    def reg_game_command(self, name, module, symbol):
        def fn(info, *args):
            self.command_play(info, name, *args)
        fn.__doc__ = module.__doc__
        setattr(self, 'command_%s' % name, fn)
        
    def add_game(self, name, module, symbol):
        module = __import__(module)
        try:
            module.setup(self.db_dir)
            self.registry[name] = (module, symbol)
            self.reg_game_command(name, module, symbol)
        except:
            self.broadcast('Failed to load %s' % name)
            raise

    def abort(self):
        if self.game:
            self.game.abort()
            self.game = None

    def reload(self):
        self.abort()
        for name, (module, symbol) in self.registry.iteritems():
            try:
                module = reload(module)
                module.setup(self.db_dir)
                self.registry[name] = (module, symbol)
                self.reg_game_command(name, module, symbol)
            except:
                self.broadcast('Failed to reload %s' % name)
                raise

    def privmsg(self, info, message):
        if info.private and self.game and self.game.catch_all_private:
            self.privmsg_rest(info, message)
        else:
            super(Manager, self).privmsg(info, message)
        
    def privmsg_rest(self, info, message):
        if self.game:
            self.game.privmsg(info, message)

#     def get_commands(self):
#         return super(Manager, self).get_commands()

#     def get_command(self, command):
#         if command in self.registry:
#             return partial(self.command_play, name = )
#         return super(Manager, self).get_command(command)
    
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

    @util.restrict(3)
    def command_abort(self, info):
        """
        Usage: $Babort$B

        Aborts the current game.
        """
        if self.game:
            game = self.game
            self.abort()
            self.broadcast('Game of %s aborted by %s.' % (game.name, info.user))
        else:
            info.respond('No game going on right now.')

    @util.restrict(3)
    def command_reload(self, info):
        """
        Usage: $Breload$B

        Reloads the current game.
        """
        self.broadcast('Games reloaded by %s.' % info.user)
        self.reload()

    def command_help(self, info, command = None):
        """
        Usage: $Bhelp <command>$B

        Provides help about the command.
        """
        if command is None:
            general = self.get_commands() #[x[8:] for x in dir(self) if x.startswith('command_')]
            general.sort()
            info.respond('$B$UGeneral commands:$U %s$B' % ', '.join(general))
            if self.game:
                game = self.game.get_commands() #[x[8:] for x in dir(self.game) if x.startswith('command_')]
                game.sort()
                info.respond('$B$U%s commands:$U %s$B' % (self.game.name, ', '.join(game)))
#             else:
#                 games = [name for name in self.registry]
#                 games.sort()
#                 info.respond('$B$UGames:$U %s$B' % ', '.join(games))
            return
        
        answer = []
        #cname = 'command_%s' % command
        #fn = getattr(self, cname, None)
        fn = self.get_command(command)
        if not fn and self.game:
            fn = self.game.get_command(command)
            #fn = getattr(self.game, cname, None)
        if not fn and command in self.registry:
            fn = self.registry[command][0]
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

    def tick(self):
        if self.game:
            try:
                self.game.tick()
            except Exception, e:
                self.abort()
                self.broadcast('An error occurred in tick(): [%s]. The game was aborted.' % e)
