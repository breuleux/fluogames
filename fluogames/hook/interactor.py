
import greenlet



class Interactor:

    def message(self, users, message):
        """
        Sends a message privately to all users.
        """
        raise NotImplementedError

    def broadcast(self, message):
        """
        Sends a message to all users.
        """
        raise NotImplementedError

    def next(self):
        """
        Returns the next command.
        """
        raise NotImplementedError
    


class StdioInteractor(Interactor):
    """
    Uses standard input/output to prompt and
    message users.
    """

    def message(self, users, message):
        print ", ".join(users) + ": " + message

    def broadcast(self, message):
        print message

    def next(self):
        return raw_input().split()



class GreenletInteractor(Interactor):
    """
    Uses coroutines to interact. The coroutine
    instantiating the Interactor should accept
    messages: 'next', 'message' and 'broadcast'.
    """

    def __init__(self):
        self.g = greenlet.getcurrent()

    def message(self, users, message):
        self.g.switch('message', users, message)

    def broadcast(self, message):
        self.g.switch('broadcast', message)

    def next(self):
        return self.g.switch('next')



def request_action(interactor, action_map):
    """
    Request actions from several users. action_map
    maps a user to a list of actions he can perform.
    The user will be prompted for an action until
    he chooses an action in the list.

    Note: don't provide an empty list for a user's
    allowed actions.
    """
    users = action_map.keys()
    for user in users:
        interactor.message(user, "Allowed actions: " + " | ".join(action_map[user]))
    result_map = {}
    while users:
        cmd = interactor.next(users)
        user, cmd = cmd[0], cmd[1:]
        if user in users:
            if cmd in action_map[user]:
                result_map[user] = cmd
                users.remove(user)
            else:
                interactor.message(user, "You cannot perform that action.")
    return result_map




