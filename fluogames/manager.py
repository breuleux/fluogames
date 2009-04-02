
import util
import game
from IPython.deep_reload import reload as dreload

class Manager(util.MiniBot):

    def __init__(self, bot, db_dir):
        super(Manager, self).__init__(bot)
        self.registry = {}
        self.game = None
        self.db_dir = db_dir

    def reg_game_command(self, name, module, hier):
        self.registry[name] = (module, hier)
        def fn(info, *args):
            self.command_play(info, name, *args)
        gclass = module
        for symbol in hier:
            gclass = getattr(gclass, symbol)
        if hasattr(gclass, 'setup'):
            gclass.setup(self.db_dir)
        fn.__doc__ = gclass.__doc__
        setattr(self, 'command_%s' % name, fn)

    def add_game(self, name, module, *hier):
        #module = __import__('.'.join((module,) + hier[:-1]), fromlist = hier[-1:])
        module = __import__(module)
        try:
            self.reg_game_command(name, module, hier)
        except:
            self.broadcast('Failed to load %s' % name)
            raise

    def abort(self):
        if self.game:
            self.game.abort()
            self.game = None

    def reload(self):
        self.abort()
        for name, (module, hier) in self.registry.iteritems():
            try:
                #module = reload(module)
                module = dreload(module, exclude = ['fluogames', 'sys', '__builtin__', '__main__'])
                m = module
                for symbol in hier[:-1]:
                    m = getattr(m, symbol)
                    reload(m)
                self.reg_game_command(name, module, hier)
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
            module, hier = self.registry[name]
        except KeyError:
            info.respond('No such game: %s' % name)
            return
        gclass = module
        for h in hier:
            gclass = getattr(gclass, h)
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

    def help(self, *topics):
        if not topics:
            answer = super(Manager, self).help()
            if self.game:
                answer2 = self.game.help()
                answer2[0] = '%s: %s' % (util.format(self.game.name, bold=True, underline=True), answer2[0].replace('$U$BCommand list$B$U: ', ''))
                answer += answer2
            return answer
        try:
            return super(Manager, self).help(*topics)
        except:
            if self.game:
                return self.game.help(*topics)
            else:
                raise
        
    def tick(self):
        if self.game:
            try:
                self.game.tick()
            except util.AbortError, e:
                self.abort()
                self.broadcast('$BGame aborted:$B %s' % e)
            except Exception, e:
                self.abort()
                self.broadcast('An error occurred in tick(): [%s]. The game was aborted.' % e)
