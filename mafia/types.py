
import mafia
import roles
import groups

class Communist(mafia.Join):

    def on_switch_in(self):
        self.min_players = 2
        self.max_players = 0
        self.starting_phase = mafia.Night
        super(Communist, self).on_switch_in()

    def on_switch_out(self):
        super(Communist, self).on_switch_out()
        self.targmap = dict((p, p) for p in self.players)
        self.comrades = groups.Melee(self, 3, name = 'Comrades', color = 'green')
        self.players = [roles.Comrade(self, player, self.comrades, 3, name = 'Comrade') for player in self.players]
        self.groups = [self.comrades]
        for player in self.players:
            self.msg(player, player.describe_private())
        self.broadcast('Factions in play:')
        self.broadcast(self.comrades.describe_public())


mafia.types.update(
    communist = Communist
    )
