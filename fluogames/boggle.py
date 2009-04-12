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
    
    language =  conf.StringOption(description =
"""The default language for playing Boggle."""
                          ),

    width = conf.NumericOption(int, min = 4, max = 8, description =
"""Width of the grid."""
                                  ),

    height = conf.NumericOption(int, min = 4, max = 8, description =
"""height of the grid."""
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
    Boggle!!!
    """

    @classmethod
    def __phases__(self):
        return dict(idle = BoggleIdle,
                    playing = BogglePlay)
    
    def setup(self):
        self.conf = configurator.load(self.loc)
        for k, v in self.conf.iteritems():
            setattr(self, k, v)
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
    
    def __call__(self, info):
        self.manager.start(self)
        self.wordlist = self.load_wordlist(self.language)
        self.broadcast('A new game of Boggle starts!', underline = True)
        self.broadcast('Link the letters horizontally, vertically and diagonally on the grid below to form words. PM the bot with as many words as you can find. You can (and should) put more than one on each line, separated by spaces.')
        letters = self.get_lang_conf(self.language)['letters']
        self.grid = self.make_grid(letters, self.width, self.height)

        self.show_grid()
        
        self.players = defaultdict(set)
        self.found = set()
        self.dups = set()
        
        self.schedulef(self.play_times, self.manager.abort)
        self.broadcast('You have %s seconds.' % self.remaining())
        self.switch(BogglePlay)


class BogglePlay(BoggleIdle):

    catchall_private = True

    def on_switch_out(self):
        scores = []
        for player, words in self.players.iteritems():
            words.difference_update(self.dups)
            if words:
                words = list(words)
                words.sort(key = lambda x: (-len(x), x))
                self.broadcast('$B%s$B found: $B%s$B' % (player, " ".join(words)))
                scores.append((len(words), player))
        if self.dups:
            words = list(self.dups)
            words.sort(key = lambda x: (-len(x), x))
            self.broadcast('More than one player found: $B%s$B' % ' '.join(words))
        scores.sort()
        if scores:
            self.broadcast('$BScores:$B %s'
                           % ', '.join('%s: %s' % (player, score)
                                       for score, player in reversed(scores)))

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
        return len(word) >= 3 and word in self.wordlist and self.is_on_grid(word)
    
    def command_grid(self, info):
        self.show_grid()

    def submit_words(self, user, words):
        userwords = self.players[user]
        valid = set()
        invalid = set()
        alreadyfound = set()
        for word in words:
            if word in userwords:
                alreadyfound.add(word)
            elif word in self.found:
                valid.add(word)
                self.dups.add(word)
            elif self.valid(word):
                valid.add(word)
                userwords.add(word)
                self.found.add(word)
            else:
                invalid.add(word)
        return valid, invalid, alreadyfound
        
#     def command_check(self, info, *words):
#         def colorize(word):
#             if self.valid(word):
#                 return format.format(word, bold = True, fg = 3)
#             else:
#                 return format.format(word, bold = False, fg = 4)
#         self.broadcast(" ".join(map(colorize, words)))
#         #self.broadcast(str([(word, word in self.wordlist, self.is_on_grid(word)) for word in words]))

    def command_words(self, info):
        words = self.players[info.user]
        if not words:
            info.reply('You found no words.')
        else:
            words = list(words)
            words.sort(key = lambda x: (-len(x), x))
            info.reply('You found $B%s$B words: %s' % (len(words), ' '.join(words)))
    
    def on_privmsg(self, info, message):
        if info.private:
            if not message[0].isalpha():
                super(BogglePlay, self).on_privmsg(info, message)
            words = message.split(" ")
            valid, invalid, alreadyfound = self.submit_words(info.user, words)
            def colorize(word):
                if word in valid:
                    return format.format(word, bold = True, fg = 3)
                elif word in alreadyfound:
                    return format.format(word, bold = False, fg = 6)
                else:
                    return format.format(word, bold = False, fg = 4)
            info.reply('%s - %s/%s valid and new (your total: %s words)' \
                           % (' '.join(map(colorize, words)),
                              len(valid),
                              len(words),
                              len(self.players[info.user])))
        else:
            super(BogglePlay, self).on_privmsg(info, message)


__fluostart__ = BoggleIdle

