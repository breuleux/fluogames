from __future__ import with_statement

import os
import util
import format
import plugin
import traceback
 

class ManagerPhases:
    
    @classmethod
    def __phases__(cls):
        return dict(idle = IdleManager,
                    playing = PlayingManager)


class IdleManager(ManagerPhases, plugin.StandardPlugin):

    def __init__(self, name, bot, loc, conf, reload = False):
        super(IdleManager, self).__init__(name, bot, loc)
        self.conf = conf
        self.prioritary_plugins = []
        self.plugins_map = {}
        self.plugins = []
        self.game = None
        for plugin in conf['plugins']:
            self.add_plugin(plugin, reload = reload)

    def on_switch_in(self):
        if self.game:
            self.prioritary_plugins.remove(self.game)
            self.game.integrated = False
            self.game = None

    def add_plugin(self, (name, module_name, enabled, integrated, prioritary), reload = False):
        if not enabled:
            return
        module = util.resolve(module_name, reload = reload)
        loc = os.path.join(self.loc, name)
        try:
            os.makedirs(loc)
        except (IOError, OSError):
            pass
        cls = module.__fluostart__
        with util.indir(loc):
            inst = cls(self, name, loc)
        inst.integrated = integrated
        if prioritary:
            self.prioritary_plugins.append(inst)
        else:
            self.plugins.append(inst)
        self.plugins_map[name] = (module_name, enabled, integrated, prioritary, inst)

    def get_plugin(self, name):
        return self.plugins_map[name][-1]

    def pub_plugins(self):
        list = []
        for plugin in self.prioritary_plugins + self.plugins:
            list.append(plugin)
            if getattr(plugin, 'catchall_public', False):
                break
        return list
    
    def priv_plugins(self):
        list = []
        for plugin in self.prioritary_plugins + self.plugins:
            list.append(plugin)
            if getattr(plugin, 'catchall_private', False):
                break
        return list

    def start(self, game):
        self.game = game
        self.switch(PlayingManager)

    def abort(self):
        raise util.UsageError('There is no game going on at the moment.')
    
    def get_commands(self, pub = False, priv = False):
        commands = super(IdleManager, self).get_commands()
        pubp = self.pub_plugins()
        privp = self.priv_plugins()
        plugins = (privp if priv
                   else (pubp if pub or len(pubp) > len(privp)
                         else privp))
        for plugin in plugins:
            if plugin.integrated:
                commands = dict(plugin.get_commands(), **commands)
            elif plugin.name not in commands and callable(plugin):
                commands[plugin.name] = plugin
        return commands

    def get_command(self, cmd, pub = False, priv = False):
        return self.get_commands(pub, priv).get(cmd, None)

    def do_command(self, info, command, args):
        fn = self.get_command(command, info.public, info.private)
        return super(IdleManager, self).do_command(info, fn, args)

    def privmsg(self, info, message):
        for plugin in self.prioritary_plugins + self.plugins:
            if hasattr(plugin, 'watch'):
                plugin.watch(info, message)
        super(IdleManager, self).privmsg(info, message)
            
    def privmsg_rest(self, info, message):
        pubp = self.pub_plugins()
        privp = self.priv_plugins()
        if info.public \
                and pubp \
                and getattr(pubp[-1], 'catchall_public', False):
            pubp[-1].privmsg(info, message)
        elif info.private \
                and privp \
                and getattr(privp[-1], 'catchall_private', False):
            privp[-1].privmsg(info, message)



class PlayingManager(IdleManager):

    def on_switch_in(self):
        if self.game:
            self.game.integrated = True
            self.prioritary_plugins.append(self.game)

    def start(self, game):
        raise util.UsageError('There is already a game of %s going on at the moment.' % format.bold(self.game.name))

    def abort(self):
        try:
            self.game.reset()
        except Exception, e:
            traceback.print_exc(e)
            self.broadcast('There was an error resetting the plugin.')
        self.switch(IdleManager)

    def help(self, *topics):
        if len(topics) and topics[0] == 'main':
            game = self.game
            self.game = None
            answer = super(PlayingManager, self).help(*topics[1:])
            self.game = game
            return answer
        if self.game:
            if not topics:
                return self.game.help() + ['This help is specifically for $B%s$B ' % self.game.name +
                                           '- for more help, type $B!help main$B, ' +
                                           'for a complete commands list type $B!help commands$B.']
            if topics[0] == 'game':
                return self.game.help(*topics[1:])
#             elif topics[0] == 'phases':
#                 return self.game.help('phases')
            elif topics[0] in self.game.__phases__():
                return self.game.help(*topics)
        return super(PlayingManager, self).help(*topics)

    def tick(self):
        try:
            if self.game:
                self.game.tick()
        except Exception, e:
            traceback.print_exc(e)
            self.broadcast('An error occurred. The game was aborted.')
            self.abort()

    def tick10(self):
        try:
            if self.game:
                self.game.tick10()
        except Exception, e:
            traceback.print_exc(e)
            self.broadcast('An error occurred. The game was aborted.')
            self.abort()






    
#     def __init__(self, bot, db_dir):
#         super(Manager, self).__init__(bot)
#         self.registry = {}
#         self.game = None
#         self.db_dir = db_dir

#     def reg_game_command(self, name, module, hier):
#         self.registry[name] = (module, hier)
#         def fn(info, *args):
#             self.command_play(info, name, *args)
#         gclass = module
#         for symbol in hier:
#             gclass = getattr(gclass, symbol)
#         if hasattr(gclass, 'setup'):
#             gclass.setup(self.db_dir)
#         fn.__doc__ = gclass.__doc__
#         setattr(self, 'command_%s' % name, fn)

#     def add_game(self, name, module, *hier):
#         #module = __import__('.'.join((module,) + hier[:-1]), fromlist = hier[-1:])
#         module = __import__(module)
#         try:
#             self.reg_game_command(name, module, hier)
#         except:
#             self.broadcast('Failed to load %s' % name)
#             raise

#     def abort(self):
#         if self.game:
#             self.game.abort()
#             self.game = None

#     def reload(self):
#         self.abort()
#         for name, (module, hier) in self.registry.iteritems():
#             try:
#                 #module = reload(module)
#                 module = dreload(module, exclude = ['fluogames', 'sys', '__builtin__', '__main__'])
#                 m = module
#                 for symbol in hier[:-1]:
#                     m = getattr(m, symbol)
#                     reload(m)
#                 self.reg_game_command(name, module, hier)
#             except:
#                 self.broadcast('Failed to reload %s' % name)
#                 raise

#     def privmsg(self, info, message):
#         try:
#             if info.private and self.game and self.game.catch_all_private:
#                 self.privmsg_rest(info, message)
#             else:
#                 super(Manager, self).privmsg(info, message)
#         except util.AbortError, e:
#             self.abort()
#             if e.message:
#                 self.broadcast(util.format('Game aborted: ', bold = True) + e.message)
        
#     def privmsg_rest(self, info, message):
#         if self.game:
#             self.game.privmsg(info, message)
    
#     @util.require_public
#     def command_play(self, info, name, *args):
#         """
#         Usage: $Bplay <game>$B

#         Start a game. You may use $<game>$ directly as a command
#         instead.
#         """
#         try:
#             module, hier = self.registry[name]
#         except KeyError:
#             info.respond('No such game: %s' % name)
#             return
#         gclass = module
#         for h in hier:
#             gclass = getattr(gclass, h)
#         if not issubclass(gclass, game.Game):
#             print gclass, gclass.__bases__, game.Game
#             print gclass.__bases__[0].__bases__
#             print gclass.__bases__[0].__bases__ == game.Game
#             gclass(self, info, *args)
#             #info.respond('No such game: %s' % name)
#         else:
#             if self.game:
#                 info.respond('There is already a game of %s going on.' % self.game.name)
#             else:
#                 try:
#                     self.game = gclass(self, name, info.channel, args)
#                     self.game.start(info)
#                 except Exception, e:
#                     self.abort()
#                     raise

#     @util.restrict(3)
#     def command_abort(self, info):
#         """
#         Usage: $Babort$B

#         Aborts the current game.
#         """
#         if self.game:
#             game = self.game
#             self.abort()
#             self.broadcast('Game of %s aborted by %s.' % (game.name, info.user))
#         else:
#             info.respond('No game going on right now.')

#     @util.restrict(3)
#     def command_reload(self, info):
#         """
#         Usage: $Breload$B

#         Reloads the current game.
#         """
#         self.broadcast('Games reloaded by %s.' % info.user)
#         self.reload()

#     def help(self, *topics):
#         if not topics:
#             answer = super(Manager, self).help()
#             if self.game:
#                 answer2 = self.game.help()
#                 answer2[0] = '%s: %s' % (util.format(self.game.name, bold=True, underline=True), answer2[0].replace('$U$BCommand list$B$U: ', ''))
#                 answer += answer2
#             return answer
#         try:
#             return super(Manager, self).help(*topics)
#         except:
#             if self.game:
#                 return self.game.help(*topics)
#             else:
#                 raise
        
#     def tick(self):
#         if self.game:
#             try:
#                 self.game.tick()
#             except util.AbortError, e:
#                 self.abort()
#                 self.broadcast('$BGame aborted:$B %s' % e)
#             except Exception, e:
#                 self.abort()
#                 self.broadcast('An error occurred in tick(): [%s]. The game was aborted.' % e)
