
import game
import util

class Witty(game.Game):

    def command_hello(self, info, target):
        """
        Usage: hello <user>

        Say hello to someone!
        """
        self.broadcast('%s says hello to %s' % (info.user, target))

    def command_bla(self, info, n1, n2):
        """
        Usage: bla <n1> <n2>

        Bla bla BLA adds n1 and n2
        """
        if not isinstance(n1, (int, float)) or not isinstance(n2, (int, float)):
            raise util.UsageError('n1 and n2 must be numbers')
        self.broadcast(str(n1 + n2))


