
import util


class Game(util.StandardPlugin):

    def __init__(self, manager, name, loc):
        super(Game, self).__init__(name, manager.bot, loc)
        self.manager = manager

    def __call__(self, info, cmd, *args):
        """
        Usage: $Bmain command arg1 arg2 ...$B
        """
        self.do_command(info, cmd, args)




# class Game(util.MiniBot):
#     catch_all_private = False
    
#     def __init__(self, manager, name, channel, arguments):
#         super(Game, self).__init__(manager.bot)
#         self.manager = manager
#         self.name = name
#         self.channel = channel
#         self.arguments = arguments

#     def start(self, info):
#         pass

#     def abort(self):
#         pass

#     def tick(self):
#         pass


# class PhasedGame(Game):

#     def schedule(self, timeouts, switch_to):
#         self.timeouts = list(timeouts)
#         self.switch_to = switch_to

#     def remaining(self):
#         return sum(self.timeouts)
        
#     def tick(self):
#         self.timeouts[0] -= 1
#         if self.timeouts[0] == 0:
#             self.timeouts[:1] = []
#             if not self.timeouts:
#                 self.switch(self.switch_to)
#             else:
#                 self.broadcast('%i seconds remaining!' % self.remaining())



