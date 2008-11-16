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
        self.factory.bots.append(self)
        irc.IRCClient.connectionMade(self)
        if not hasattr(self, 'manager'):
            self.manager = manager.Manager(self, self.factory.db_dir)
            self.manager.add_game('witty', 'witty', 'Witty')

    def connectionLost(self, reason):
        self.factory.bots.remove(self)
        irc.IRCClient.connectionLost(self, reason)

    # callbacks for events

    def signedOn(self):
        self.join(self.factory.channel)

    def joined(self, channel):
        pass

    def privmsg(self, user, channel, msg):
        self.manager.privmsg(util.Info(self, user, channel), msg)

    def broadcast(self, message, color = False, bold = False, underline = False):
        self.msg(self.factory.channel, message, color, bold, underline)

    def msg(self, user, message, color = False, bold = False, underline = False):
        message = util.wrap_msg(message, color, bold, underline)
        message = message.replace('$B', '\002')
        message = message.replace('$C', '\003')
        message = message.replace('$U', '\037')
        irc.IRCClient.msg(self, user, message)

    def notice(self, user, message, color = False, bold = False, underline = False):
        message = util.wrap_msg(message, color, bold, underline)
        message = message.replace('$B', '\002')
        message = message.replace('$C', '\003')
        message = message.replace('$U', '\037')
        irc.IRCClient.notice(self, user, message)

    def tick(self):
        self.manager.tick()


class GameBotFactory(protocol.ClientFactory):
    protocol = GameBot

    def __init__(self, channel, nickname = None, nickpass = None, db_dir = None):
        self.channel = channel
        self.nickname = nickname
        self.nickpass = nickpass
        self.db_dir = db_dir
        self.bots = []

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()

    def tick(self):
        for bot in self.bots:
            bot.tick()



if __name__ == '__main__':
    f = GameBotFactory(sys.argv[1], db_dir = 'db')
    reactor.connectTCP("irc.dejatoons.net", 6667, f)
    l = task.LoopingCall(f.tick)
    l.start(1.0)
    reactor.run()

