
import game
import util

class Countdown(game.Game):
    """
    Usage: countdown <n>

    Count down n seconds.
    """
    def start(self, info):
        if not self.arguments:
            self.timeout = 3
        else:
            self.timeout = self.arguments[0]
            if not isinstance(self.timeout, int) or self.timeout < 0 or self.timeout > 5:
                raise util.UsageError('Please specify a valid number of seconds (0 <= n <= 5)')
        self.tick()
    def tick(self):
        if self.timeout == 0:
            self.broadcast('GO!')
            self.manager.abort()
        else:
            self.broadcast(str(self.timeout))
            self.timeout -= 1
