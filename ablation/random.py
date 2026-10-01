from snake_game import Action, Controller
import random

from snake_game.game import GameState


class RandomController(Controller):
    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def get_action(self, state: GameState) -> Action | None:
        return self.rng.choice(list(Action))

    def reset(self) -> None:
        return super().reset()