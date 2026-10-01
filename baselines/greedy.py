from snake_game import Action, Controller, GameState
from baselines.bfs import moves, step, any_safe_move


class GreedyController(Controller):
    def get_action(self, state: GameState) -> Action | None:
        # one move ahead: of the moves that don't hit the body, take the one closest to the food
        if state.food is None:
            return any_safe_move(state)
        walls = set(state.snake[:-1])  # the tail moves out of the way
        safe = [action for action in moves(state) if step(state, state.head, action) not in walls]
        if not safe:
            return None  # trapped either way
        return min(safe, key=lambda action: distance(state, step(state, state.head, action), state.food))


def distance(state, a, b):
    # steps between two cells on a board whose edges wrap
    dx = abs(a[0] - b[0]) % state.width
    dy = abs(a[1] - b[1]) % state.height
    return min(dx, state.width - dx) + min(dy, state.height - dy)
