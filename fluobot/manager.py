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
            self.game.enabled = True
            self.game = None

    def add_plugin(self, (name, module_name, enabled, integrated, prioritary), reload = False):
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
        inst.enabled = enabled
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
            if plugin.enabled and getattr(plugin, 'catchall_public', False):
                break
        return list
    
    def priv_plugins(self):
        list = []
        for plugin in self.prioritary_plugins + self.plugins:
            list.append(plugin)
            if plugin.enabled and getattr(plugin, 'catchall_private', False):
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
            if not plugin.enabled:
                continue
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
                and pubp[-1].enabled \
                and getattr(pubp[-1], 'catchall_public', False):
            pubp[-1].privmsg(info, message)
        elif info.private \
                and privp \
                and privp[-1].enabled \
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

