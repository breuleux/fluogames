from __future__ import with_statement

from fluobot import util
from fluobot import plugin
from fluobot import conf
from fluobot import format

import os
import urllib
import random
from collections import defaultdict


configurator = conf.Configurator(
    
    play_times = conf.ObjectOption(description =
"""List of times, in seconds. sum(submit_times) is the duration of the
playing phase. Each element of the list marks a point where the
user will be told how much time remains."""
                               ),
    
    grid_change_time = conf.NumericOption(int, description =
"""Number of seconds into a game during which the user can change the
grid."""
                                  ),
    
    language =  conf.StringOption(description =
"""The default language for playing Boggle."""
                          ),

    min_word_length = conf.NumericOption(int, description =
"""Minimum length that the submitted words must have to be accepted."""
                                  ),

    width = conf.NumericOption(int, min = 4, max = 8, description =
"""Width of the grid."""
                                  ),

    height = conf.NumericOption(int, min = 4, max = 8, description =
"""Height of the grid."""
                                  ),
    
    can_configure = conf.ObjectOption(description =
"""List of configuration keys that can be configured when starting the
game."""
                                  ),
    )

lang_configurator = conf.Configurator(
    
    letters = conf.ObjectOption(description =
"""List of characters that may appear in the grid. Each character is
associated to an integer representing how likely it is to be picked
up. Basically, each tile will be drawn from a "bag" where each letter
is represented N times. Note: the characters are case insensitive."""
                               ),
    
    wordlist_url =  conf.StringOption(description =
"""Location of the wordlist to use on the internet. This will be
downloaded automatically by fluoboggle and renamed into "dict.txt" the
first time you use this language in a game of boggle. It will only
download from this url if there is no file called dict.txt. If you
want, you can download it yourself beforehand."""
                          )
    )



class BoggleIdle(plugin.ScheduledPlugin):
    """
    Boggle is a word game where you are given a grid of letters and
    you have to link them horizontally, vertically or diagonally to
    form words. You score points for each word you find (more points
    for longer words), but only if other players didn't find it as
    well!
    """

    @classmethod
    def __phases__(self):
        return dict(idle = BoggleIdle,
                    playing = BogglePlay)

    def reset_conf(self):
        for k, v in self.conf.iteritems():
            setattr(self, k, v)
    
    def setup(self):
        try:
            self.conf = configurator.load(self.loc)
        except IOError:
            raise IOError('A conf.py file is required for the %s game (fluogames.boggle) in %s' % (self.name, os.path.join(self.loc, 'conf.py')))
        self.reset_conf()
        self._loaded_wordlists = {}
        self.lang_conf = {}
        with util.indir(self.loc):
            for lang in os.listdir('.'):
                if os.path.isdir(lang) \
                        and os.path.exists(os.path.join(lang, 'conf.py')):
                    self.lang_conf[lang] = lang_configurator.load(lang)

    def get_lang_conf(self, language):
        if language not in self.lang_conf:
            raise util.UsageError('There is no wordlist available in %s' % language)
        return self.lang_conf[language]

    def load_wordlist(self, language):
        if language in self._loaded_wordlists:
            return self._loaded_wordlists[language]
        
        conf = self.get_lang_conf(language)
        with util.indir(self.loc):
            dict_file = os.path.join(language, 'dict.txt')
            if not os.path.exists(os.path.join(language, 'dict.txt')):
                print 'downloading %s' % language
                urllib.urlretrieve(conf['wordlist_url'], dict_file)
            with open(dict_file, 'r') as f:
                print 'reading %s' % dict_file
                words = frozenset(map(str.strip, f.readlines()))
                self._loaded_wordlists[language] = words
            return words

    def make_grid(self, letters, width, height):
        total = sum(x[1] for x in letters)
        grid = [[None for j in xrange(width)] for i in xrange(height)]

        for i in xrange(height):
            for j in xrange(width):
                v = random.randint(1, total)
                for letter, n in letters:
                    v -= n
                    if v <= 0:
                        grid[i][j] = letter
                        break

        return grid

    def show_grid(self):
        for row in self.grid:
            self.broadcast(' '.join(row))

    def show_grid_priv(self, info):
        for row in self.grid:
            info.reply(' '.join(row))

    @plugin.require_public
    def __call__(self, info, *configure):
        self.reset_conf()
        for entry in configure:
            try:
                k, v = entry.split('=')
            except:
                raise util.UsageError('The parameters must be of the form key=value, with key in: %s' % ', '.join(self.can_configure))
            if k not in self.can_configure:
                raise util.UsageError('Cannot configure parameter %s (it might not exist).' % k)
            try:
                setattr(self, k, configurator.filter(k, v, strict = True))
            except Exception, e:
                raise util.UsageError('Error configuring %s: %s' % (k, e.message))
            
        self.wordlist = self.load_wordlist(self.language)
        self.manager.start(self)
        self.broadcast('A new game of Boggle starts!', underline = True)
        self.broadcast(format.blockify(
                """
                Link the letters horizontally, vertically and diagonally
                on the grid below to form words. PM the bot with as many
                words as you can find. You can (and should) put more than
                one on each line, separated by spaces. The minimum length
                for a word to be accepted is $B%s$B. Language is $B%s$B.
                """
                ) % (self.min_word_length, self.language))
        self.switch(BogglePlay)


class BogglePlay(BoggleIdle):
    """
    Link the letters horizontally, vertically and diagonally on the
    grid of letters (you can type !grid to see it). PM the bot with as
    many words as you can find. You can (and should) put more than one
    on each line, separated by spaces. Type !words to check what words
    you've found so far.
    """

    catchall_private = True

    def on_switch_in(self):
        letters = self.get_lang_conf(self.language)['letters']
        self.grid = self.make_grid(letters, self.width, self.height)

        self.show_grid()

        self.submit_queue = defaultdict(list)
        
        self.players = defaultdict(set)
        self.found = set()
        self.dups = set()

        self.total_time = sum(self.play_times)
        self.schedulef(self.play_times, self.manager.abort)
        self.broadcast('You have %s seconds.' % self.remaining())

    def on_switch_out(self):
        self.empty_queue()
        scores = []
        p = list(self.players.iteritems())
        p.sort()
        for player, words in p:
            if words:
                n, score = self.score_words(words, self.dups)
                self.broadcast('$B%s$B found: %s (%s unique words for %s points)' \
                                   % (player, self.format_words(words, self.dups), n, score))
                scores.append((score, player))
        scores.sort()
        if scores:
            self.broadcast('$BScores:$B %s'
                           % ', '.join('%s: %s' % (player, score)
                                       for score, player in reversed(scores)))
    
    def command_grid(self, info):
        """
        Usage: $Bgrid$B

        Show the grid of letters.
        """
        if info.public:
            self.show_grid()
        else:
            self.show_grid_priv(info)

    def command_words(self, info):
        """
        Usage: $Bwords$B

        Show all the words you found so far in this round.
        """
        words = self.players[info.user]
        if not words:
            info.reply('You found no words.')
        else:
            n, score = self.score_words(words, self.dups)
            info.reply('%s (%s words for %s points)'
                       % (self.format_words(words, self.dups), n, score))
            
    def command_check(self, info, word):
        """
        Usage: $Bcheck <word>$B
        
        Check if the word is in the dictionary, that it is on the grid
        and that it is long enough. You can use this during the game
        if you want to know why one of your words was rejected.
        """
        word = word.lower()
        
        if word not in self.wordlist:
            info.reply('%s is not in the %s wordlist.' % (format.format(word, fg = 4), self.language))

        elif not self.is_on_grid(word):
            info.reply('%s is a word, but it cannot be formed on the grid.' % format.format(word, fg = 4))

        elif len(word) < self.min_word_length:
            info.reply('%s is a word and can be found on the grid, but it is not long enough (it needs to be at least $B%s$B letters long).'
                       % (format.format(word, fg = 4), self.min_word_length))

        else:
            pts = len(word) - self.min_word_length + 1
            info.reply('%s is valid and worth $B%s$B point%s.' % (format.format(word, bold = True, fg = 3), pts, 's' if pts > 1 else ''))

    @plugin.restrict(1)
    def command_newgrid(self, info):
        """
        Usage: $Bnewgrid$B

        Generate a new grid.
        """
        if (self.total_time - self.remaining()) > self.grid_change_time:
            info.reply('You can only change the grid in the first %s seconds of the game.' % self.grid_change_time)
        else:
            self.switch(BogglePlay)
            
    def on_privmsg(self, info, message):
        if info.private:
            if not message[0].isalpha():
                return super(BogglePlay, self).on_privmsg(info, message)
            words = map(str.lower, message.split(" "))
            self.submit_queue[info.user] += words
            #self.empty_queue()
        else:
            super(BogglePlay, self).on_privmsg(info, message)

    def empty_queue(self):
        for user, words in self.submit_queue.iteritems():
            valid, invalid, alreadyfound = self.submit_words(user, words)
            def colorize(word):
                if word in valid:
                    return format.format(word, bold = True, fg = 3)
                elif word in alreadyfound:
                    return format.format(word, bold = False, fg = 6)
                else:
                    return format.format(word, bold = False, fg = 4)
            self.notice(user,
                        '%s - %s/%s valid and new (your total: %s words)' \
                            % (' '.join(map(colorize, words)),
                               len(valid),
                               len(words),
                               len(self.players[user])))
            
        self.submit_queue = defaultdict(list)

    def tick(self):
        if self.remaining() % 5 == 0:
            # We only submit the words every 5 seconds, that way the
            # bot doesn't flood out from giving feedback when people
            # submit one word per line.
            self.empty_queue()
        super(BogglePlay, self).tick()

    def is_on_grid(self, word):
        letters = list(word)
        n = len(letters)
        w = self.width
        h = self.height
        used = [[False] * w for i in xrange(h)]
        def helper(i, j, k):
            if i < 0 or j < 0 or i >= h or j >= w:
                return False
            if used[i][j]:
                return False
            if self.grid[i][j] == letters[k]:
                if k == n-1:
                    return True
                else:
                    used[i][j] = True
                    k2 = k + 1
                    rval = helper(i+1, j, k2) \
                        or helper(i-1, j, k2) \
                        or helper(i, j+1, k2) \
                        or helper(i, j-1, k2) \
                        or helper(i-1, j-1, k2) \
                        or helper(i-1, j+1, k2) \
                        or helper(i+1, j-1, k2) \
                        or helper(i+1, j+1, k2)
                    if not rval:
                        used[i][j] = False
                    return rval
            else:
                return False
        for i in xrange(h):
            for j in xrange(w):
                if helper(i, j, 0):
                    return True
        return False

    def valid(self, word):
        return len(word) >= self.min_word_length and word in self.wordlist and self.is_on_grid(word)

    def submit_words(self, user, words):
        userwords = self.players[user]
        valid = set()
        invalid = set()
        alreadyfound = set()
        for word in words:
            if word in userwords:
                alreadyfound.add(word)
            elif word in self.found:
                userwords.add(word)
                valid.add(word)
                self.dups.add(word)
            elif self.valid(word):
                valid.add(word)
                userwords.add(word)
                self.found.add(word)
            else:
                invalid.add(word)
        return valid, invalid, alreadyfound
        
    def format_words(self, words, dups):
        by_len = defaultdict(list)
        for word in words:
            by_len[len(word)].append(word)
        s = []
        def colorize(word): 
            if word in dups:
                return format.format(word, bold = False)
            else:
                return format.format(word, bold = True)
        l = list(by_len.iteritems())
        l.sort()
        l.reverse()
        for n, words in l:
            words.sort()
            s.append(' '.join(map(colorize, words)))
        return '[%s]' % ' | '.join(s)

    def score_words(self, words, dups):
        score = 0
        n = 0
        for word in words:
            if word not in dups:
                n += 1
                score += (len(word) - self.min_word_length + 1)
        return n, score


__fluostart__ = BoggleIdle

