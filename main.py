#! /usr/bin/env python

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, task

from random import randint, shuffle
from copy import copy
import greenlet

import sys

import manager
import util

class GameBot(irc.IRCClient):

    nickname = "LEGO"

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        if not hasattr(self, 'manager'):
            self.manager = manager.Manager(self)
            self.manager.add_game('witty', 'witty', 'Witty')

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    # callbacks for events

    def signedOn(self):
        self.join(self.factory.channel)

    def joined(self, channel):
        pass

    def privmsg(self, user, channel, msg):
        self.manager.privmsg(util.Info(self, user, channel), msg)
            

    
#     def privmsg(self, user, channel, msg):
#         print user, channel, msg
#         try:
#             user, host = user.split('!', 1)
#         except ValueError:
#             return
#         if channel == self.factory.channel:
#             if msg == '!reload':
#                 game = self.game
#                 if game:
#                     self.game = None
#                     game.abort(user, host)
#                 self.factory.make_registry()
#                 self.broadcast('reloaded by %s' % user)
#             elif msg == '!abort':
#                 game = self.game
#                 if game:
#                     self.game = None
#                     game.abort(user, host)
#                 self.broadcast('stopped by %s' % user)
#             elif self.game:
#                 self.game.privmsg(user, host, channel, msg)
#             elif msg and msg[0] == '!':
#                 msg = msg.split()
#                 name = msg[0][1:]
#                 self.game = self.factory.registry[name](self, name, channel, msg[1:])
#                 self.game.start(user, host)
#         elif self.game:
#             self.game.privmsg(user, host, channel, msg)

    def broadcast(self, message):
        self.msg(self.factory.channel, message)

    def msg(self, user, message):
        message = message.replace('$B', '\002')
        message = message.replace('$U', '\003')
        irc.IRCClient.msg(self, user, message)

    def notice(self, user, message):
        message = message.replace('$B', '\002')
        message = message.replace('$U', '\003')
        irc.IRCClient.notice(self, user, message)



class GameBotFactory(protocol.ClientFactory):
    protocol = GameBot

    def __init__(self, channel, nickname = None, nickpass = None):
        self.channel = channel
        self.nickname = nickname
        self.nickpass = nickpass

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()



if __name__ == '__main__':
    f = GameBotFactory(sys.argv[1])
    reactor.connectTCP("irc.dejatoons.net", 6667, f)
    reactor.run()

