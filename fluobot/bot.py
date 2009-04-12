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

    def make_user(self, user):
        if isinstance(user, User):
            return user
        u = User(user)
        u.clearance = 0
        return u

    def get_user(self, user):
        return self.make_user(user)
    
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

    def irc_PONG(self, *args):
        pass
        
    # callbacks for events

    def signedOn(self):
        if self.nickname != self.conf['nickname'] and self.conf['autoghost']:
            self.msg('NickServ', 'ghost %s %s' % (self.conf['nickname'], self.conf['nickpass']))
        self.msg('NickServ', 'identify %s' % self.nickpass)
        self.join(self.channel)

    def irc_NOTICE(self, prefix, params):
        # Normally, after ghosting successfully, nickserv notices
        # something back with the word 'ghost' in it. That's probably
        # as generic as it can be :(
        if prefix.split('!', 1)[0] == 'NickServ' \
                and 'ghost' in params[1].lower() \
                and self.nickname != self.conf['nickname']:
            self.setNick(self.conf['nickname'])
            self.msg('NickServ', 'identify %s' % self.nickpass)

    def kickedFrom(self, channel, kicker, message):
        self.join(channel)
        
    def privmsg(self, user, channel, msg):
        user = self.get_user(user)
        if user:
            self.manager.on_privmsg(Info(self, user, channel), msg)

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
        self.user_status = {}

    def get_user(self, user):
        u = FluoBot.get_user(self, user)
        if u.nick.lower() not in self.user_status:
            return u
        u.clearance = max(self.user_status[u.nick.lower()])
        return u

    def clearance(self, user):
        return self.get_user(user).clearance

        
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
            self.user_status[name.lower()] = perms

    def userJoined(self, user, channel):
        FluoBot.userJoined(self, user, channel)
        u = self.make_user(user)
        nick = u.nick.lower()
        self.user_status[nick] = [0]

    def userKicked(self, kickee, channel, kicker, message):
        FluoBot.userKicked(self, kickee, channel, kicker, message)
        u = self.get_user(kickee)
        del self.user_status[u.nick.lower()]
        
    def userLeft(self, user, channel):
        FluoBot.userLeft(self, user, channel)
        u = self.get_user(user)
        del self.user_status[u.nick.lower()]

    def userQuit(self, user, message):
        FluoBot.userQuit(self, user, message)
        u = self.get_user(user)
        del self.user_status[u.nick.lower()]

    def userRenamed(self, oldname, newname):
        FluoBot.userRenamed(self, oldname, newname)
        oldname, newname = oldname.lower(), newname.lower()
        self.user_status[newname] = self.user_status[oldname]
        del self.user_status[oldname]

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
            maps = dict(q=5, a=4, o=3, h=2, v=1)
            if mode in maps:
                perms = self.user_status[arg.lower()]
                if adding:
                    perms.append(maps[mode])
                    #self.user_status[arg.lower()].append(maps[mode])
                else:
                    perms.remove(maps[mode])
                    #self.user_status[arg.lower()].remove(maps[mode])



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

    def keep_alive(self):
        for bot in self.bots:
            bot.sendLine('PING %s' % self.conf['network'])
            #bot.ping(self.conf['network'], 'what')


def start(conf):
    f = FluoBotFactory(conf)
    reactor.connectTCP(conf['network'], 6667, f)
    t1 = task.LoopingCall(f.tick)
    t1.start(1.0)
    t2 = task.LoopingCall(f.tick10)
    t2.start(0.1)
    t3 = task.LoopingCall(f.keep_alive)
    t3.start(30.0)
    reactor.run()




################
# CONFIGURATOR #
################

from conf import Configurator, PathOption, StringOption, BoolOption
import util
import os

configurator = Configurator(

    protocol = StringOption(description =
"""The subclass of FluoBot that will be instantiated in order to run
the bot."""
                        ),

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
    
    autoghost = BoolOption(description =
"""If its nickname is taken and autoghost is True, the bot will
automatically try to ghost it (forcefully disconnect it) and change
back to its original nickname."""
                             ),

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
    protocol = 'fluobot.bot.ChanAuthFluoBot',
    root = "~/.fluobot",
    #network = "",
    #channel = "",
    #nickname = "",
    nickpass = "",
    #nicksuffix = '_',
    reconnect = 'y',
    autoghost = 'y',
    autoload_plugins = 'y',
    public_prefix = "!",
    private_prefix = "! ",
    )

