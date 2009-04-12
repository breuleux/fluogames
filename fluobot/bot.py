#! /usr/bin/env python

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, task

import sys
import os

import util
import manager
from info import Info, User
import format

class FluoBot(irc.IRCClient):

    def reload_conf(self):
        self.conf = configurator.load(self.conf['root'])

    def clearance(self, user):
        return 0
        
    def make_user(self, nickname):
        try:
            u = User(nickname)
            u.clearance = 0
        except:
            u = None
        return u

    def get_user(self, nickname):
        return self.make_user(nickname)
    
    def make_manager(self, reload = False):
        self.manager = manager.IdleManager('manager', self, os.path.join(self.conf['root'], 'data'), self.conf, reload = reload)

    def connectionMade(self):
        print "Connection made."

        self.factory.bots.append(self)
        
        self.conf = self.factory.conf

        self.channel = self.conf['channel']
        self.nickname = self.conf['nickname']
        self.nickpass = self.conf['nickpass']

        self.users_pool = {}
        
        irc.IRCClient.connectionMade(self)
        if not hasattr(self, 'manager'):
            self.make_manager()

    def connectionLost(self, reason):
        print "Connection lost."
        self.factory.bots.remove(self)
        irc.IRCClient.connectionLost(self, reason)

#     def lineReceived(self, line):
#         print line
#         irc.IRCClient.lineReceived(self, line)

    # callbacks for events

    def signedOn(self):
        self.msg('NickServ', 'identify %s' % self.nickpass)
        self.join(self.channel)

    def kickedFrom(self, channel, kicker, message):
        self.join(channel)
        
    def privmsg(self, user, channel, msg):
        self.manager.on_privmsg(Info(self, self.get_user(user), channel), msg)

    def broadcast(self, message, bold = False, underline = False, fg = False, bg = False):
        self.msg(self.channel, message, bold, underline, fg, bg)

    def msg(self, user, message, bold = False, underline = False, fg = False, bg = False):
        if isinstance(message, (list, tuple)):
            for m in message:
                self.msg(user, m, bold, underline, fg, bg)
            return
        else:
            message = str(message)
        message = format.format(message, bold, underline, fg, bg)
        for m in message.split('\n'):
            if m:
                irc.IRCClient.msg(self, user, m)

    def notice(self, user, message, bold = False, underline = False, fg = False, bg = False):
        if isinstance(message, (list, tuple)):
            for m in message:
                self.notice(user, m, bold, underline, fg, bg)
            return
        else:
            message = str(message)
        message = format.format(message, bold, underline, fg, bg)
        for m in message.split('\n'):
            if m:
                irc.IRCClient.notice(self, user, m)

    def tick(self):
        self.manager.tick()

    def tick10(self):
        self.manager.tick10()


class ChanAuthFluoBot(FluoBot):


    def connectionMade(self):
        FluoBot.connectionMade(self)
        self.reset_users()

    def reset_users(self):
        self.users = {}
        self.user_status = {}

    def get_user(self, user):
        if isinstance(user, User):
            return user
        if '!' in user:
            nick, host = user.split('!', 1)
            u = self.users.get(nick.lower(), None)
            if u and u.host == 'UNCHECKED':
                u.host = host
            return u
        else:
            return self.users.get(user.lower(), None)

    def destroy_user(self, user):
        u = self.get_user(user)
        del self.users[u.nick.lower()]
        del self.user_status[u]
    
    def clearance(self, user):
        return self.get_user(user).clearance
    
#     def make_user(self, nickname):
#         return 
# #         if isinstance(nickname, User):
# #             return nickname
# #         try:
# #             u = User(nickname)
# #             u.clearance = max(self.user_status.get(u.nick.lower(), [0]))
# #         except Exception, e:
# #             u = None
# #         return u

        
    def joined(self, channel):
        FluoBot.joined(self, channel)
        self.reset_users()
        self.sendLine("NAMES %s" % channel)

    def irc_RPL_NAMREPLY(self, prefix, params):
        for name in params[3].split():
            pfx = ['+', '%', '@', '&', '~']
            perms = [0]
            while name[0] in pfx:
                perms.append(pfx.index(name[0]) + 1)
                name = name[1:]
            if name == self.nickname:
                continue
            u = self.make_user(name + '!UNCHECKED')
            u.clearance = max(perms)
            self.users[name.lower()] = u
            self.user_status[u] = perms
        print 'use', self.users
        print 'ust', self.user_status

    def irc_JOIN(self, user, channel):
        #FluoBot.userJoined(self, user, channel)
        print 'join:', user
        u = self.make_user(user)
        u.clearance = 0
        self.users[u.nick.lower()] = u
        self.user_status[u] = [0]
        #self.user_status[user.split('!', 1)[0].lower()] = [0]
        print 'use', self.users
        print 'ust', self.user_status

    def userKicked(self, kickee, channel, kicker, message):
        FluoBot.userKicked(self, kickee, channel, kicker, message)
        print 'kicked:', kickee
        self.destroy_user(kickee)
        print 'use', self.users
        print 'ust', self.user_status
        
    def irc_PART(self, user, channel):
        print 'left:', user
        self.destroy_user(user)
        print 'use', self.users
        print 'ust', self.user_status

    def userQuit(self, user, message):
        print 'quit:', user
        FluoBot.userQuit(self, user, message)
        self.destroy_user(user)
        print 'use', self.users
        print 'ust', self.user_status

    def userRenamed(self, oldname, newname):
        print 'rename %s -> %s' % (oldname, newname)
        FluoBot.userRenamed(self, oldname, newname)
        u = self.get_user(oldname)
        u.nick = newname
        del self.users[oldname.lower()]
        self.users[newname.lower()] = u
        print 'use', self.users
        print 'ust', self.user_status
        
        #self.user_status[newname.lower()] = self.user_status[oldname.lower()]
        #del self.user_status[oldname.lower()]

    def modeChanged(self, user, channel, set, modes, args):
        FluoBot.modeChanged(self, user, channel, set, modes, args)
        changes = []
        adding = set
        for c in modes:
            if c == '+': adding = True
            elif c == '-': adding = False
            else: changes.append((c, adding))
        changes = changes[-len(args):]
        for (mode, adding), arg in zip(changes, args):
            u = self.get_user(arg)
            maps = dict(q=5, a=4, o=3, h=2, v=1)
            if mode in maps:
                perms = self.user_status[u]
                if adding:
                    perms.append(maps[mode])
                    #self.user_status[arg.lower()].append(maps[mode])
                else:
                    perms.remove(maps[mode])
                    #self.user_status[arg.lower()].remove(maps[mode])
                u.clearance = max(perms)
        print 'use', self.users
        print 'ust', self.user_status



class FluoBotFactory(protocol.ClientFactory):

    def __init__(self, conf):
        self.bots = []
        self.conf = conf
        self.protocol = util.resolve(conf['protocol'])

    def clientConnectionLost(self, connector, reason):
        if self.conf['reconnect']:
            print "Reconnecting..."
            connector.connect()
        else:
            reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        if self.conf['reconnect']:
            connector.connect()
        else:
            reactor.stop()

    def tick(self):
        for bot in self.bots:
            bot.tick()

    def tick10(self):
        for bot in self.bots:
            bot.tick10()



def start(conf):
    f = FluoBotFactory(conf)
    reactor.connectTCP(conf['network'], 6667, f)
    t1 = task.LoopingCall(f.tick)
    t1.start(1.0)
    t2 = task.LoopingCall(f.tick10)
    t2.start(0.1)
    reactor.run()




################
# CONFIGURATOR #
################

from conf import Configurator, PathOption, StringOption, BoolOption
import util
import os

configurator = Configurator(

    root = PathOption(description =        
"""The root of the configuration and the database(s) used by the bot
and the games. Running "fluobot run" with no arguments will by default
use the configuration in ~/.fluobot, but you may pass a different
configuration directory if you wish. The directory you specify will be
created if it does not already exist."""
                        ),
    
    network = StringOption(min_length = 1, description = 
"""Network that the bot should connect to."""
                           ),
    
    channel = StringOption(min_length = 1, description =
"""Channel that the bot should join."""
                           ),
    
    nickname = StringOption(min_length = 1, description =
"""Nickname of the bot"""
                            ),
    
    nickpass = StringOption(description =
"""Password for the bot's nickname"""
                            ),
    
#     nicksuffix = StringOption(description = 
# """Suffix to append to the nickname if it is already occupied (could be
# added multiple times). The bot will try to use the same pass."""
#                               ),
    
    reconnect = BoolOption(description = 
"""If reconnect is True, the bot will automatically try to connect to
the network again if it is disconnected."""
                             ),
    
    autoload_plugins = BoolOption(description = 
"""If True, any package located in the /plugins directory will be
loaded automatically."""
                             ),
    
#     autoghost = BoolOption(description =
# """If its nickname is taken and autoghost is True, the bot will
# automatically try to ghost it (forcefully disconnect it) and change
# back to its original nickname."""
#                              ),

    public_prefix = StringOption(description =
"""Default prefix for commands when entered in a channel. You can give
more than one prefix if you separate them with spaces. For example,
public_prefix = '! @' would allow you to use !command or @command. You
can have multi-character prefixes, but put the longer prefixes
before. If public_prefix = ' ' or if it ends with a space, then no
prefix will be needed to use commands."""
                                 ),

    private_prefix = StringOption(description =
"""Default prefix for commands when entered in private. You can give
more than one prefix if you separate them with spaces. For example,
public_prefix = '! @' would allow you to use !command or @command. You
can have multi-character prefixes, but put the longer prefixes
before. If public_prefix = ' ' or if it ends with a space, then no
prefix will be needed to use commands."""
                                 ),

    auth = StringOption(description =
"""Module to use to identify nicknames to an account and
to handle their permissions.
fluobot.auth.natural requires no logging in and uses
 operator status in order to grant permissions"""
                        ),
    )

conf_defaults = dict(
    root = "~/.fluobot",
    #network = "",
    #channel = "",
    #nickname = "",
    nickpass = "",
    #nicksuffix = '_',
    reconnect = 'y',
    #autoghost = 'y',
    autoload_plugins = 'y',
    public_prefix = "!",
    private_prefix = "! ",
    auth = "fluobot.plugins.chanauth",
    )

