
import game
import util
import os
import random

from collections import defaultdict


__fluogame__ = True
__fluoname__ = 'witty'


prompt_source = None

def pjoin(prompt):
    return ' '.join(map(str, prompt))


class Witty(game.PhasedGame):
    """
    Witty is a game where you must complete prompts in the wittiest ways
    possible :) - each round, all players must vote for the entry they
    prefer and they score points for the votes they receive.

    Each round is played in two phases: submit and vote. During the submit
    phase, PM the bot with $Bsubmit <entry>$B. Once the submit phase is
    over, all entries will be listed in numerical order without their
    authors' names. During the voting phase, PM the bot with $Bvote
    <entry#>$B. You will only get points if you vote!
    """

    catch_all_private = True

    @staticmethod
    def setup(db_dir):
        global prompt_source
        prompt_source = MultiPrompt(
            (0.45, FilePrompt(os.path.join(db_dir, 'witty', 'prompts.txt')), 'text'),
            (0.10, DirPrompt(os.path.join(db_dir, 'witty', 'ircquote')), 'ircquote'),
            (0.00, XVsYPrompt(os.path.join(db_dir, 'witty', 'rpsi.txt')), 'rpsi'),
            (0.45, DirPrompt(os.path.join(db_dir, 'witty', 'parametrized')), 'parametrized'),
            )

    def __init__(self, manager, name, channel, arguments):
        super(Witty, self).__init__(manager, name, channel, arguments)
        self.submit_times = [30, 20, 10]
        self.min_vote_time = 30
        self.seconds_per_entry_vote = 5
        self.wait_times = [5]
        self.max_strikes = 2
        self.max_bonus = 3
        self.min_entries = 3
        self.color = dict(fg = 0, bg = 1)
        self.color_prompt_prefix = dict(fg = 4, bg = self.color['bg'])
        self.color_prompt = dict(fg = 8, bg = self.color['bg'])
        self.color_entrynum = dict(fg = 4, bg = self.color['bg'])
        self.color_entry = dict(fg = 9, bg = self.color['bg'])
        self.color_entry_vote = dict(fg = 11, bg = self.color['bg'])
    
    def start(self, info):
        if self.arguments:
            self.do_command(info, self.arguments[0], self.arguments[1:])
            self.manager.abort()
            return
        self.strikes = 0
        self.players = set()
        self.points = defaultdict(int)
        self.pts = []
        self.broadcast('A new game of Witty starts!', underline = True)
        self.switch(Submit)
        
    def on_switch_in(self):
        if self.strikes >= self.max_strikes:
            self.broadcast('Game canceled due to inactivity.')
            self.manager.abort()
        if self.pts:
            lead = self.pts[0][0]
            if lead >= 20 or self.strikes >= self.max_strikes:
                winners = [user for (p, user) in self.pts if p == lead]
                if len(winners) == 1:
                    self.broadcast('Winner: %s' % winners[0])
                else:
                    self.broadcast('Winners: %s' % ', '.join(winners))
                self.manager.abort()
                return
        if self.manager.game is self:
            self.schedule(self.wait_times, Submit)
            self.broadcast('Next witty round in %i seconds!' % self.remaining())

    def command_add_prompt(self, info, category, *prompt):
        """
        Usage: $Badd_prompt <category> <prompt>$B

        Add a prompt to Witty.
        """
        if not prompt:
            raise util.UsageError()
        prompt_source.add_prompt(category, *prompt)
        prompt_source.save()
        info.respond('Added prompt: %s' % pjoin(prompt))

    def command_delete_prompt(self, info, category, *prompt):
        """
        Usage: $Bdelete_prompt <prompt>$B

        Delete a prompt.
        """
        if not prompt:
            raise util.UsageError()
        prompt_source.delete_prompt(category, *prompt)
        prompt_source.save()
        info.respond('Deleted prompt: %s' % pjoin(prompt))

    def command_save(self, info):
        """
        Usage: $Bsave$B

        Saves all prompts to the current database's prompts.
        """
        prompt_source.save()
        info.respond('Successfully saved the prompts.')
    
    def broadcast(self, message, bold = False, underline = False):
        super(Witty, self).broadcast(message, bold, underline, **self.color)



class Submit(Witty):

    def on_switch_in(self):
        self.submittals = {}
        self.n = 0
        self.prompt = prompt_source.generate(self)
        self.broadcast('%s%s' % (
                util.format('Prompt: ', **self.color_prompt_prefix),
                util.format(self.prompt, **self.color_prompt)))
        self.schedule(self.submit_times, Vote)
        self.broadcast('You have %i seconds to submit.' % self.remaining())

    def command_status(self, info):
        """
        Usage: $Bstatus$B

        Prints out the current prompt and the time remaining
        """
        info.respond('$B%i seconds to submit for:$B %s' % (self.remaining(), self.prompt))

    @util.restrict(1)
    @util.require_public
    def command_next(self, info):
        """
        Usage: $Bnext$B

        Discards the current prompt and shows a new one.
        """
        self.broadcast('Okay, okay... next one!')
        self.on_switch_in()

    @util.require_private
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
            info.respond('You have revised your entry: %s' % message)
        else:
            self.n += 1
            self.players.add(info.user)
            self.submittals[info.user] = [self.n, message]
            self.broadcast('%s%s%s' % (
                    util.format('[', **self.color),
                    util.format(str(self.n), **self.color_entrynum),
                    util.format('] was submitted!', **self.color)))

    def privmsg_rest(self, info, message):
        if info.private:
            self.do_command(info, 'submit', (message, ))
            

class Vote(Witty):

    def on_switch_in(self):
        self.entries = [(y, x) for (x, y) in self.submittals.items()]
        if len(self.entries) < self.min_entries:
            self.strikes += 1
            self.broadcast('Time out! Unfortunately, we need at least %i entries to play.' % self.min_entries)
            self.switch(Witty, switch_out = False)
            return
        self.strikes = 0
        self.entries.sort()
        self.votes = {}
        self.broadcast('Time out! Here are the entries:')
        self.broadcast('%s%s' % (
                util.format('Prompt: ', **self.color_prompt_prefix),
                util.format(self.prompt, **self.color_prompt)))
        for (i, entry), user in self.entries:
            self.broadcast('%(leftbrack)s%(num)s%(rightbrack)s%(entry)s' % dict(
                    leftbrack = util.format('[', **self.color),
                    num = util.format(str(i), **self.color_entrynum),
                    rightbrack = util.format('] ', **self.color),
                    entry = util.format(entry, **self.color_entry)
                    ))
                    
        total = self.min_vote_time + self.seconds_per_entry_vote * len(self.entries)
        self.schedule([total - total/2, total/2], Witty)
        self.broadcast('You have %i seconds to vote.' % self.remaining())

    def on_switch_out(self):
        votes = self.votes.items()
        self.tally = []
        padding = max(len(user) for (_, user) in self.entries) + 1
        _v = [[user2 for user2, vote in votes if vote == i] for ((i, entry), user) in self.entries]
        padding_v = max(len(str(len(v))) for v in _v) + 2
        self.broadcast('%s%s' % (
                util.format('Prompt: ', **self.color_prompt_prefix),
                util.format(self.prompt, **self.color_prompt)))
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
                msg = 'Votes: %s' % (', '.join(v))
            self.broadcast('%(leftbrack)s%(num)s%(rightbrack)s%(user)s%(points)s%(entry)s%(votes)s' % dict(
                leftbrack = util.format('[', **self.color),
                num = util.format(str(i), **self.color_entrynum),
                rightbrack = util.format('] ', **self.color),
                user = util.format(user.ljust(padding), **self.color),
                points = util.format(p.ljust(padding_v), **self.color),
                entry = util.format(entry, **self.color_entry_vote),
                votes = util.format(' | ' + msg, **self.color)
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
        info.respond('%i seconds remaining to vote.' % self.remaining())

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
                self.switch(Witty)
            else:
                info.respond('You voted for entry #%i' % n)
        else:
            info.respond('You must play to vote.')

    def privmsg_rest(self, info, message):
        if info.private:
            try:
                self.do_command(info, 'vote', (int(message),))
            except ValueError:
                pass




###################

class PromptSource(object):
    def generate(self, game):
        raise NotImplementedError
    def add_prompt(self, *prompt):
        raise NotImplementedError
    def delete_prompt(self, *prompt):
        raise NotImplementedError
    def save(self):
        raise NotImplementedError
    def reload(self):
        raise NotImplementedError

class MultiPrompt(PromptSource):
    def __init__(self, *subsources):
        self.subsources = []
        self.quick_find = {}
        sp = 0
        for p, ss, name in subsources[:-1]:
            sp += p
            self.subsources.append((sp, ss, name))
            self.quick_find[name] = ss
        p, ss, name = subsources[-1]
        if not p:
            assert sp < 1.0
        else:
            assert sp + p == 1.0
        self.subsources.append((1.0, ss, name))
        self.quick_find[name] = ss
    def generate(self, game):
        r = random.random()
        for p, ss, name in self.subsources:
            if r < p:
                return ss.generate(game)
        raise Exception('how the fuck did we get here?', r, self.subsources)
    def add_prompt(self, category, *prompt):
        if not prompt:
            raise util.UsageError('Not enough arguments to add_prompt')
        try:
            self.quick_find[category].add_prompt(*prompt)
        except KeyError:
            raise util.UsageError('Unknown category: %s. Accepted categories are: %s'
                                  % (category, ', '.join(self.quick_find.keys())))
    def delete_prompt(self, category, *prompt):
        if not prompt:
            raise util.UsageError('Not enough arguments to add_prompt')
        try:
            self.quick_find[category].delete_prompt(*prompt)
        except KeyError:
            raise util.UsageError('Unknown category: %s. Accepted categories are: %s'
                                  % (category, ', '.join(self.quick_find.keys())))
    def save(self):
        for p, ss, name in self.subsources:
            ss.save()
    def reload(self):
        for p, ss, name in self.subsources:
            ss.reload()

class FilePrompt(PromptSource):
    def __init__(self, file):
        self.file = file
        self.load()
        self.changed = False
    def generate(self, game):
        return random.choice(self.db)
    def add_prompt(self, *prompt):
        if not prompt:
            raise util.UsageError('Not enough arguments to add_prompt')
        prompt = pjoin(prompt)
        self.db.append(prompt)
        self.changed = True
    def delete_prompt(self, *prompt):
        if not prompt:
            raise util.UsageError('Not enough arguments to add_prompt')
        prompt = pjoin(prompt)
        try:
            self.db.remove(prompt)
            self.changed = True
        except:
            raise util.UsageError('Could not find prompt: %s' % prompt)
    def load(self):
        self.db = map(str.strip, open(self.file).readlines())
    def save(self):
        if self.changed:
            f = open(self.file, 'w')
            f.write('\n'.join(self.db))
            f.write('\n')
            f.close()
        self.changed = False
    def reload(self):
        self.save()
        self.load()

class DirPrompt(PromptSource):
    def __init__(self, dir):
        files = os.listdir(dir)
        if 'main.txt' not in files:
            raise Exception('There must be a file named main.txt in %s' % dir)
        self.dir = dir
        files = [file for file in files if file.endswith('.txt')]
        self.files = files
        self.db = {}
        self.load()
        self.changed = defaultdict(bool)
    def generate(self, game):
        d = {}
        for k, v in self.db.iteritems():
            d[k] = random.choice(v)
        players = list(game.players)
        if not players: players = ['someone']
        d['user'] = random.choice(players)
        main = d.pop('main')
        main %= d
        return main
    def add_prompt(self, file, *prompt):
        if not prompt:
            raise util.UsageError('Not enough arguments to add_prompt')
        prompt = pjoin(prompt)
        if file not in self.db:
            raise util.UsageError('Must add a prompt to one of these files: %s' % ', '.join(self.db.keys()))
        self.db[file].append(prompt)
        self.changed[file] = True
    def delete_prompt(self, file, *prompt):
        if not prompt:
            raise util.UsageError('Not enough arguments to add_prompt')
        prompt = pjoin(prompt)
        if file not in self.db:
            raise util.UsageError('Must delete a prompt from one of these files: %s' % ', '.join(self.db.keys()))
        try:
            self.db[file].remove(prompt)
            self.changed[file] = True
        except:
            raise util.UsageError('Could not find prompt: %s' % prompt)
    def load(self):
        for file in self.files:
            self.db[file[:-4]] = map(str.strip, open(os.path.join(self.dir, file)).readlines())
    def save(self):
        for file in self.files:
            _file = file[:-4]
            if self.changed[_file]:
                f = open(os.path.join(self.dir, file), 'w')
                f.write('\n'.join(self.db[_file]))
                f.write('\n')
                f.close()
            self.changed[_file] = False
    def reload(self):
        self.save()
        self.load()

class XVsYPrompt(FilePrompt):
    def generate(self, game):
        a, b = None, None
        while a == b:
            a = super(XVsYPrompt, self).generate(game)
            b = super(XVsYPrompt, self).generate(game)
        return '$C4$BFIGHT!$B$C $B%s$B vs. $B%s$B' % (a, b)

