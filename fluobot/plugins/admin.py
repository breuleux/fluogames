
from fluobot.format import bold
from fluobot.util import UsageError
from fluobot.plugin import ManagedPlugin
from fluobot import plugin
import traceback


class Admin(ManagedPlugin):
    """
    Administrative tools for fluobot. Contains the $Badmin$B,
    $Breload$B, $Benable$B and $Bdisable$B commands.
    """
    
    @plugin.restrict(1)
    def command_abort(self, info):
        """
        Usage: $B!abort$B

        Aborts the current game. All unsaved progress on that game
        will be lost and the bot will be ready to host another
        game. If there is no game going on, does nothing.        
        """
        
        try:
            game_name = self.manager.game.name
        except:
            pass # if there's no game self.manager.abort will raise a UsageError anyway
        self.manager.abort()
        self.broadcast('Aborted %s game on request from %s.' % (bold(game_name), bold(info.user)))

    @plugin.restrict(3)
    def command_reload(self, info, plugin = None):
        """
        Usage: $B!reload$B or $B!reload <plugin>$B

        If used with no argument, reloads all plugins. The current
        game is aborted. If used with an argument, reloads the
        specified plugin.
        """

        try:
            if plugin is None:
                # reload everything completely
                self.bot.reload_conf()
                self.bot.make_manager(reload = True)
                # this and the rest will get garbage collected
                info.reply("Reloaded everything.")
                return

            try:
                module, enabled, integrated, prioritary, inst = self.manager.plugins_map[plugin]
            except KeyError:
                raise UsageError('Plugin %s does not exist.' % plugin)

            del self.manager.plugins_map[plugin]
            if prioritary:
                self.manager.prioritary_plugins.remove(inst)
            else:
                self.manager.plugins.remove(inst)
            self.manager.add_plugin((plugin, module, enabled, integrated, prioritary), reload = True)

            info.reply("Reloaded %s." % plugin)
        except Exception, e:
            traceback.print_exc(e)
            info.reply("There was an error during reloading: %s" % e)

    @plugin.restrict(3)
    def command_enable(self, info, plugin):
        """
        Usage: $B!enable <plugin>$B

        Enables the specified plugin. This is not persistent:
        enabling/disabling a plugin will only last until reloading or
        rebooting the bot.
        """

        try:
            self.manager.get_plugin(plugin).enabled = True
            self.broadcast('%s is enabled.' % plugin)
        except KeyError:
            raise UsageError('Plugin %s does not exist.' % plugin)

    @plugin.restrict(3)
    def command_disable(self, info, plugin):
        """
        Usage: $B!disable <plugin>$B

        Disables the specified plugin. This is not persistent:
        enabling/disabling a plugin will only last until reloading or
        rebooting the bot.
        """

        try:
            self.manager.get_plugin(plugin).enabled = False
            self.broadcast('%s is disabled.' % plugin)
        except KeyError:
            raise UsageError('Plugin %s does not exist.' % plugin)



__fluostart__ = Admin


