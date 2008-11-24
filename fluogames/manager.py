
import util
import game

class Manager(util.MiniBot):

    def __init__(self, bot, db_dir):
        super(Manager, self).__init__(bot)
        self.registry = {}
        self.game = None
        self.db_dir = db_dir

    def reg_game_command(self, name, module, symbol):
        if hasattr(module, 'setup'):
            module.setup(self.db_dir)
        self.registry[name] = (module, symbol)
        def fn(info, *args):
            self.command_play(info, name, *args)
        fn.__doc__ = getattr(module, symbol).__doc__
        setattr(self, 'command_%s' % name, fn)

    def add_game(self, name, module, symbol):
        module = __import__(module)
        try:
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
            print name, (module, symbol)
            try:
                module = reload(module)
                self.reg_game_command(name, module, symbol)
            except:
                self.broadcast('Failed to reload %s' % name)
                raise

    def privmsg(self, info, message):
        try:
            if info.private and self.game and self.game.catch_all_private:
                self.privmsg_rest(info, message)
            else:
                super(Manager, self).privmsg(info, message)
        except util.AbortError, e:
            self.abort()
            if e.message:
                self.broadcast(util.format('Game aborted: ', bold = True) + e.message)
        
    def privmsg_rest(self, info, message):
        if self.game:
            self.game.privmsg(info, message)
    
    @util.require_public
    def command_play(self, info, name, *args):
        """
        Usage: $Bplay <game>$B

        Start a game. You may use $<game>$ directly as a command
        instead.
        """
        try:
            module, symbol = self.registry[name]
        except KeyError:
            info.respond('No such game: %s' % name)
            return
        gclass = getattr(module, symbol)
        if not issubclass(gclass, game.Game):
            print gclass, gclass.__bases__, game.Game
            print gclass.__bases__[0].__bases__
            print gclass.__bases__[0].__bases__ == game.Game
            gclass(self, info, *args)
            #info.respond('No such game: %s' % name)
        else:
            if self.game:
                info.respond('There is already a game of %s going on.' % self.game.name)
            else:
                try:
                    self.game = gclass(self, name, info.channel, args)
                    self.game.start(info)
                except Exception, e:
                    self.abort()
                    raise

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

    def tick(self):
        if self.game:
            try:
                self.game.tick()
            except Exception, e:
                self.abort()
                self.broadcast('An error occurred in tick(): [%s]. The game was aborted.' % e)
