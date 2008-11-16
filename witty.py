
import game
import util
import os
import random

from collections import defaultdict


witty_db = []

def setup(db_dir):
    global witty_db
    witty_db = map(str.strip, open(os.path.join(db_dir, 'witty', 'prompts.txt')).readlines())


class Witty(game.Game):

    def __init__(self, manager, name, channel, arguments):
        super(Witty, self).__init__(manager, name, channel, arguments)
        self.submit_times = [30, 20, 10]
        self.vote_times = [45, 30, 15]
        self.wait_times = [5]
        self.max_strikes = 2
        self.min_entries = 1

    def schedule(self, timeouts, switch_to):
        self.timeouts = list(timeouts)
        self.switch_to = switch_to

    def remaining(self):
        return sum(self.timeouts)
        
    def on_switch_in(self):
        if self.strikes >= self.max_strikes:
            self.broadcast('Game canceled due to inactivity.')
            self.manager.abort()
        if self.pts:
            lead = self.pts[0][0]
            if lead >= 20 or self.strikes >= self.max_strikes:
                winners = [user for (p, user) in pts if p == lead]
                if len(winners) == 1:
                    self.broadcast('Winner: %s' % winners[0], bold = True)
                else:
                    self.broadcast('Winners: %s' % ', '.join(winners), bold = True)
                self.manager.abort()
                return
        if self.manager.game is self:
            self.schedule(self.wait_times, Submit)
            self.broadcast('Next witty round in %i seconds!' % self.remaining(), bold = True)

    def start(self, info):
        self.strikes = 0
        self.points = defaultdict(int)
        self.pts = []
        self.broadcast('A new game of Witty starts!', bold = True, underline = True)
        #self.timeouts = [100]
        self.switch(Submit)

    def tick(self):
        self.timeouts[0] -= 1
        if self.timeouts[0] == 0:
            self.timeouts[:1] = []
            if not self.timeouts:
                self.switch(self.switch_to)
            else:
                self.broadcast('%i seconds remaining!' % self.remaining(), bold = True)



class Submit(Witty):

    def on_switch_in(self):
        self.submittals = {}
        self.n = 0
        self.prompt = random.choice(witty_db)
        self.broadcast('$BPrompt:$B %s' % self.prompt)
        self.schedule(self.submit_times, Vote)
        self.broadcast('$BYou have %i seconds to submit.$B' % self.remaining())

    def command_status(self, info):
        """
        Usage: $Bstatus$B

        Prints out the current prompt and the time remaining
        """
        self.broadcast('$B%i seconds to submit for:$B %s' % (self.remaining(), self.prompt))
        
    def command_next(self, info):
        """
        Usage: $Bnext$B

        Discards the current prompt and shows a new one.
        """
        self.broadcast('Okay, okay... next one!')
        self.on_switch_in()
    
    def command_submit(self, info, *message):
        """
        Usage: $Bsubmit <entry>$B

        Submit an entry which completes the prompt.
        """
        if not message:
            raise util.UsageError('You must submit something!')
        message = ' '.join(map(str, message))
        if info.user in self.submittals:
            self.submittals[info.user][1] = message
        else:
            self.n += 1
            self.submittals[info.user] = [self.n, message]
            self.broadcast('$B[$B$C4$B$B%i$C$B] was submitted!$B' % self.n)


class Vote(Witty):

    def on_switch_in(self):
        self.entries = [(y, x) for (x, y) in self.submittals.items()]
        if len(self.entries) < self.min_entries:
            self.strikes += 1
            self.broadcast('Time out! Unfortunately, we need at least %i entries to play.' % self.min_entries, bold = True)
            self.switch(Witty, switch_out = False)
            return
        self.strikes = 0
        self.entries.sort()
        self.votes = {}
        self.broadcast('Time out! Here are the entries:', bold = True)
        self.broadcast('$BPrompt:$B %s' % self.prompt)
        for (i, entry), user in self.entries:
            self.broadcast('$B[$B$C4$B$B%i$C$B]$B $C12$B$B%s' % (i, entry))
        self.schedule(self.vote_times, Witty)
        self.broadcast('You have %i seconds to vote.' % self.remaining(), bold = True)

    def on_switch_out(self):
        votes = self.votes.items()
        for (i, entry), user in self.entries:
            msg = '$B[$B$C4$B$B%i$C$B]$B $C12$B$B%s$C | $B%s$B | ' % (i, entry, user)
            v = [user2 for user2, vote in votes if vote == i]
            nv = len(v)
            if nv == 0:
                msg += 'No votes.'
            else:
                if nv == 1:
                    msg += '1 vote '
                else:
                    msg += '%i votes ' % nv
                msg += '(%s)' % (', '.join(v))
            self.broadcast(msg)
            if user not in self.votes:
                self.broadcast('$B%s$B did not vote... no point for him or her!' % user)
            else:
                if nv:
                    self.points[user] += nv
        pts = [(y, x) for (x, y) in self.points.items()]
        pts.sort(key = lambda (x, y): (-x, y))
        if pts:
            self.broadcast('$BScore:$B ' + ', '.join('$B%s$B: %i' % (user, p) for (p, user) in pts))
        self.pts = pts

    def command_status(self, info):
        """
        Usage: $Bstatus$B

        Prints out how much time left there is to vote.
        """
        self.broadcast('%i seconds remaining to vote.' % self.remaining(), bold = True)

    def command_vote(self, info, n):
        """
        Usage: $Bvote <entry number>$B

        You must vote for one of the entries listed. You may only vote
        if you submitted something and you may not vote for yourself.
        """
        if not isinstance(n, int) or n <= 0 or n > len(self.entries):
            raise util.UsageError('Please vote for an entry from 1 to %i' % len(self.entries))
        if info.user in self.submittals:
            if self.submittals[info.user][0] == n:
                raise util.UsageError('You can\'t vote for yourself!')
            self.votes[info.user] = n
            if len(self.votes) == len(self.entries):
                self.broadcast('All votes are in!', bold = True)
                self.switch(Witty)
            else:
                info.respond('You voted for entry #%i' % n)
        else:
            info.respond('You must play to vote.')

