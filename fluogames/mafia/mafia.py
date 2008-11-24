"""
Lalala mafia
"""

from .. import game
from .. import util
from ..util import UsageError
from .. import hook

import os
import random


types = dict()
roles = dict()


class Player(util.MiniBot):

    def __init__(self, bot, game, transition):
        super(Player, self).__init__(bot)
        self.game = game
        self.transition = transition
    
    def assign(self, group, user):
        pass



class Mafia(game.PhasedGame):
    
    def __init__(self, manager, name, channel, arguments):
        super(Mafia, self).__init__(manager, name, channel, arguments)
        self.color = dict(fg = False, bg = False)
        self.join_times = [30, 20, 10]
        self.night_times = [30, 30]
        self.vote_times = [45, 35, 10]

    def start(self, info):
        if self.arguments:
            self.type_name = self.arguments[0]
        else:
            self.type_name = 'normal'
        try:
            self.type = types[self.type_name]
        except KeyError:
            raise UsageError('Unknown mafia game type: %s (available types are: %s)'
                             % (self.type_name, ', '.join(sorted(types.keys()))))
        self.broadcast('A new game of %s mafia starts!' % self.type_name)
        self.switch(self.type)

    def broadcast(self, message, bold = False, underline = False):
        super(Mafia, self).broadcast(message, bold, underline, **self.color)


class Join(Mafia):

    def on_switch_in(self):
        self.announce = []
        self.unannounce = []
        self.players = []
        self.schedule(self.join_times, self.starting_phase)

    def on_switch_out(self):
        if len(self.players) < self.min_players:
            raise util.AbortError('There are not enough players. At least %i are required.'
                                  % self.min_players)
        
    def command_join(self, info):
        if info.user in self.players:
            raise UsageError('You already joined!')
        self.announce.append(info.user)
        self.players.append(info.user)
        if len(self.players) == self.max_players:
            self.switch(self.starting_phase)

    def command_remove(self, info):
        try:
            self.players.remove(info.user)
            self.unannounce.append(info.user)
        except:
            raise UsageError('You had not joined!')

    def tick(self):
        for l, txt in ((self.announce, 'joined'), (self.unannounce, 'unjoined')):
            n = len(l)
            l[:], l = [], map(util.bold, l)
            if n == 1:
                self.broadcast('%s has %s!' % (l[0], txt))
            elif n > 1:
                self.broadcast('%s and %s have %s!' % (', '.join(l[:-1]), l[-1], txt))
        super(Join, self).tick()


class Night(Mafia):
    pass


class Day(Mafia):
    pass

