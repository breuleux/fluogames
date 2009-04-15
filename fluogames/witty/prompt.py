
import os
import random
from fluobot import util

from collections import defaultdict


def pjoin(prompt):
    return ' '.join(prompt)


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



