

from fluobot import util
from fluobot import plugin
from fluobot import conf
from fluobot import format


#     catch_all_private = True

#     @staticmethod
#     def setup(db_dir):
#         global prompt_source
#         prompt_source = MultiPrompt(
#             (0.45, FilePrompt(os.path.join(db_dir, 'witty', 'prompts.txt')), 'text'),
#             (0.10, DirPrompt(os.path.join(db_dir, 'witty', 'ircquote')), 'ircquote'),
#             (0.00, XVsYPrompt(os.path.join(db_dir, 'witty', 'rpsi.txt')), 'rpsi'),
#             (0.45, DirPrompt(os.path.join(db_dir, 'witty', 'parametrized')), 'parametrized'),
#             )
    
#     def __init__(self, manager, name, channel, arguments):
#         super(Witty, self).__init__(manager, name, channel, arguments)
#         self.submit_times = [30, 20, 10]
#         self.min_vote_time = 30
#         self.seconds_per_entry_vote = 5
#         self.wait_times = [5]
#         self.max_strikes = 2
#         self.max_bonus = 3
#         self.min_entries = 3
#         self.color = dict(fg = 0, bg = 1)
#         self.color_prompt_prefix = dict(fg = 4, bg = self.color['bg'])
#         self.color_prompt = dict(fg = 8, bg = self.color['bg'])
#         self.color_entrynum = dict(fg = 4, bg = self.color['bg'])
#         self.color_entry = dict(fg = 9, bg = self.color['bg'])
#         self.color_entry_vote = dict(fg = 11, bg = self.color['bg'])

#     def start(self, info):
#         if self.arguments:
#             self.do_command(info, self.arguments[0], self.arguments[1:])
#             self.manager.abort()
#             return
#         self.strikes = 0
#         self.players = set()
#         self.points = defaultdict(int)
#         self.pts = []
#         self.broadcast('A new game of Witty starts!', underline = True)
#         self.switch(Submit)



from collections import defaultdict


def pjoin(prompt):
    return ' '.join(prompt)


configurator = conf.Configurator(
    
    submit_times = conf.ObjectOption(description =
"""List of times, in seconds. sum(submit_times) is the duration of the
submitting phase. Each element of the list marks a point where the
user will be told how much time remains."""
                               ),
    
    points_to_win = conf.NumericOption(int, description =
"""Number of points required for someone to win (if more than one user
gets over that threshold, the highest score wins)."""
                                  ),

    min_vote_time = conf.NumericOption(int, description =
"""Minimal time for voting."""
                                  ),

    seconds_per_entry_vote = conf.NumericOption(int, description =
"""Number of seconds added to the voting time for each entry."""
                                           ),
    
    wait_times = conf.ObjectOption(description =
"""List of times, in seconds. sum(wait_times) is the duration of the
waiting phase between two rounds. Each element of the list marks a
point where the user will be told how much time remains."""
                               ),

    max_strikes = conf.NumericOption(int, description =
"""Maximal number of failed attempts to play before the game times
out because of inactivity."""
                                           ),

    max_bonus = conf.NumericOption(int, description =
"""Maximal bonus for winning a round."""
                                           ),

    min_entries = conf.NumericOption(int, description =
"""Minimal number of entries to play a round."""
                                           ),

    color =  conf.ObjectOption(description =
"""Color for the text while playing witty. Must be a dictionary with a
fg entry and a bg entry."""
                          ),

    color_prompt_prefix =  conf.ObjectOption(description =
"""Color for the prompt prefix. Must be a dictionary with a
fg entry and a bg entry."""
                          ),

    color_prompt =  conf.ObjectOption(description =
"""Color for the prompt. Must be a dictionary with a
fg entry and a bg entry."""
                          ),

    color_entrynum =  conf.ObjectOption(description =
"""Color for the entry number. Must be a dictionary with a
fg entry and a bg entry."""
                          ),

    color_entry =  conf.ObjectOption(description =
"""Color for a player's entry before voting. Must be a dictionary with a
fg entry and a bg entry."""
                          ),

    color_entry_vote =  conf.ObjectOption(description =
"""Color for a player's entry when scoring. Must be a dictionary with a
fg entry and a bg entry."""
                          ),

    prompt_source =  conf.ObjectOption(description =
"""A PromptSource instance that generates prompts for the bot."""
                          ),

    
    )


class WittyIdle(plugin.ScheduledPlugin):
    """
    Witty is a game where you must complete prompts in the wittiest
    ways possible :) - each round, all players must vote for the entry
    they prefer and they score points for the votes they receive.

    Each round is played in two phases: submit and vote. During the
    submit phase, PM the bot with your $B<entry>$B. Once the submit
    phase is over, all entries will be listed in numerical order
    without their authors' names. During the voting phase, PM the bot
    with $Bvote <entry#>$B. You will only get points if you vote!
    """

    @classmethod
    def __phases__(self):
        return dict(idle = WittyIdle,
                    submitting = WittySubmit,
                    voting = WittyVote,
                    waiting = WittyWait)
    
    def setup(self):
        self.conf = configurator.load(self.loc)
        for k, v in self.conf.iteritems():
            setattr(self, k, v)

    def __call__(self, info):
        self.manager.start(self)
        self.strikes = 0
        self.players = set()
        self.points = defaultdict(int)
        self.pts = []
        self.broadcast('A new game of Witty starts!', underline = True)
        self.switch(WittySubmit)

    def command_add_prompt(self, info, category, *prompt):
        """
        Usage: $Badd_prompt <category> <prompt>$B

        Add a prompt to Witty.
        """
        if not prompt:
            raise util.UsageError()
        self.prompt_source.add_prompt(category, *prompt)
        self.prompt_source.save()
        info.reply('Added prompt: %s' % pjoin(prompt))

    def command_delete_prompt(self, info, category, *prompt):
        """
        Usage: $Bdelete_prompt <prompt>$B

        Delete a prompt.
        """
        if not prompt:
            raise util.UsageError()
        self.prompt_source.delete_prompt(category, *prompt)
        self.prompt_source.save()
        info.reply('Deleted prompt: %s' % pjoin(prompt))

    def command_save(self, info):
        """
        Usage: $Bsave$B

        Saves all prompts to the current database's prompts.
        """
        self.prompt_source.save()
        info.reply('Successfully saved the prompts.')
    
    def broadcast(self, message, bold = False, underline = False):
        super(WittyIdle, self).broadcast(message, bold, underline, **self.color)


class WittySubmit(WittyIdle):
    """
    PM the bot an entry that completes the current prompt.
    """

    catchall_private = True

    def on_switch_in(self):
        self.submittals = {}
        self.n = 0
        self.prompt = self.prompt_source.generate(self)
        self.broadcast('%s%s' % (
                format.format('Prompt: ', **self.color_prompt_prefix),
                format.format(self.prompt, **self.color_prompt)))
        self.schedule(self.submit_times, WittyVote)
        self.broadcast('You have %i seconds to submit.' % self.remaining())

    def command_status(self, info):
        """
        Usage: $Bstatus$B

        Prints out the current prompt and the time remaining
        """
        info.reply('$B%i seconds to submit for:$B %s' % (self.remaining(), self.prompt))

    @plugin.restrict(1)
    @plugin.require_public
    def command_next(self, info):
        """
        Usage: $Bnext$B

        Discards the current prompt and shows a new one.
        """
        self.broadcast('Okay, okay... next one!')
        self.on_switch_in()

    def submit(self, info, *message):
#         """
#         Usage: $Bsubmit <entry>$B

#         Submit an entry which completes the prompt.
#         """
        
        if not message:
            raise util.UsageError('You must submit something!')
        message = ' '.join(map(str, message))
        if info.user in self.submittals:
            self.submittals[info.user][1] = message
            info.reply('You have revised your entry: %s' % message)
        else:
            self.n += 1
            self.players.add(info.user)
            self.submittals[info.user] = [self.n, message]
            self.broadcast('%s%s%s' % (
                    format.format('[', **self.color),
                    format.format(str(self.n), **self.color_entrynum),
                    format.format('] was submitted!', **self.color)))

    def on_privmsg_rest(self, info, message):
        if info.private:
            self.submit(info, message)
            #self.do_command(info, 'submit', (message, ))


class WittyVote(WittyIdle):

    catchall_private = True
    
    def on_switch_in(self):
        self.entries = [(y, x) for (x, y) in self.submittals.items()]
        if len(self.entries) < self.min_entries:
            self.strikes += 1
            self.broadcast('Time out! Unfortunately, we need at least %i entries to play.' % self.min_entries)
            self.switch(WittyWait, switch_out = False)
            return
        self.strikes = 0
        self.entries.sort()
        self.votes = {}
        self.broadcast('Time out! Here are the entries:')
        self.broadcast('%s%s' % (
                format.format('Prompt: ', **self.color_prompt_prefix),
                format.format(self.prompt, **self.color_prompt)))
        for (i, entry), user in self.entries:
            self.broadcast('%(leftbrack)s%(num)s%(rightbrack)s%(entry)s' % dict(
                    leftbrack = format.format('[', **self.color),
                    num = format.format(str(i), **self.color_entrynum),
                    rightbrack = format.format('] ', **self.color),
                    entry = format.format(entry, **self.color_entry)
                    ))
                    
        total = self.min_vote_time + self.seconds_per_entry_vote * len(self.entries)
        self.schedule([total - total/2, total/2], WittyWait)
        self.broadcast('You have %i seconds to vote.' % self.remaining())

    def on_switch_out(self):
        votes = self.votes.items()
        self.tally = []
        padding = max(len(user) for (_, user) in self.entries) + 1
        _v = [[user2 for user2, vote in votes if vote == i] for ((i, entry), user) in self.entries]
        padding_v = max(len(str(len(v))) for v in _v) + 2
        self.broadcast('%s%s' % (
                format.format('Prompt: ', **self.color_prompt_prefix),
                format.format(self.prompt, **self.color_prompt)))
        for ((i, entry), user), v in zip(self.entries, _v):
            nv = len(v)
            if nv == 0: p = ''
            elif user not in self.votes: p = ''
            else: p = '+%i' % nv
#             if nv == 0:
#                 msg = 'No votes.'
#             else:
#                 if nv == 1:
#                     msg = '1 vote '
#                 else:
#                     msg = '%i votes ' % nv
#                 msg += '(%s)' % (', '.join(v))
            if nv == 0:
                msg = 'No votes.'
            else:
                msg = 'Votes: %s' % (', '.join(map(str, v)))
            self.broadcast('%(leftbrack)s%(num)s%(rightbrack)s%(user)s%(points)s%(entry)s%(votes)s' % dict(
                leftbrack = format.format('[', **self.color),
                num = format.format(str(i), **self.color_entrynum),
                rightbrack = format.format('] ', **self.color),
                user = format.format(str(user).ljust(padding), **self.color),
                points = format.format(p.ljust(padding_v), **self.color),
                entry = format.format(entry, **self.color_entry_vote),
                votes = format.format(' | ' + msg, **self.color)
                ))
            if user not in self.votes:
                self.broadcast('$B%s$B did not vote... no point for him or her!' % user)
            else:
                if nv:
                    self.tally.append([nv, user])
                    self.points[user] += nv
        self.tally.sort(key = lambda (x, y): (-x, y))
        if len(self.tally) >= 2 and self.tally[0][0] > self.tally[1][0]:
            user = self.tally[0][1]
            bonus = self.tally[0][0] - self.tally[1][0]
            bonus = min(bonus, self.max_bonus)
            self.tally[0][0] += bonus
            self.broadcast('$B%s$B gets a bonus of %i points for first place!' % (user, bonus))
            self.points[user] += bonus
        pts = [(y, x) for (x, y) in self.points.items()]
        pts.sort(key = lambda (x, y): (-x, y))
        if pts:
            self.broadcast('Score: ' + ', '.join('%s: %i' % (user, p) for (p, user) in pts))
        self.pts = pts

    def command_status(self, info):
        """
        Usage: $Bstatus$B

        Prints out how much time left there is to vote.
        """
        info.reply('%i seconds remaining to vote.' % self.remaining())

    @plugin.autoparse
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
                self.broadcast('All votes are in!')
                self.switch(WittyWait)
            else:
                info.reply('You voted for entry #%i' % n)
        else:
            info.reply('You must play to vote.')

    def on_privmsg_rest(self, info, message):
        if info.private:
            try:
                self.do_command(info, 'vote', (int(message),))
            except ValueError:
                pass



class WittyWait(WittyIdle):

    def on_switch_in(self):
        if self.strikes >= self.max_strikes:
            self.broadcast('Game canceled due to inactivity.')
            self.manager.abort()
        if self.pts:
            lead = self.pts[0][0]
            if lead >= self.points_to_win or self.strikes >= self.max_strikes:
                winners = [user for (p, user) in self.pts if p == lead]
                if len(winners) == 1:
                    self.broadcast('Winner: %s' % winners[0])
                else:
                    self.broadcast('Winners: %s' % ', '.join(winners))
                self.manager.abort()
                return
        if self.manager.game is self:
            self.schedule(self.wait_times, WittySubmit)
            self.broadcast('Next witty round in %i seconds!' % self.remaining())

