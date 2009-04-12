
from fluobot.plugin import ManagedPlugin


class ChanAuth(ManagedPlugin):
    """    
    Authorization plugin for fluobot. This plugin uses the channel's
    modes to give users a certain clearance:
    
    0 = no status;
    1 = + = voice;
    2 = % = half-op;
    3 = @ = operator;
    4 = & = administrator;
    5 = ~ = owner;
    """
    
    def command_clearance(self, info, user = None):
        """
        Usage: $B!clearance$B or $B!clearance user$B

        Returns the clearance level of the specified user. If no user
        is specified, returns the clearance level of the user who
        issued the command.
        """
        if user:
            info.reply('%s has clearance level %s' % (user, self.bot.clearance(user)))
        else:
            info.reply('You have clearance level %s' % self.bot.clearance(info.user))
        


__fluostart__ = ChanAuth


