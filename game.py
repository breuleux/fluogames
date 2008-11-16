
import util

class Game(util.MiniBot):

    def __init__(self, manager, name, channel, arguments):
        super(Game, self).__init__(manager.bot)
        self.manager = manager
        self.name = name
        self.channel = channel
        self.arguments = arguments

    def start(self, info):
        pass

    def abort(self):
        pass

    def tick(self):
        pass
    
        

