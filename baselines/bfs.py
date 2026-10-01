from collections import deque

from snake_game import Action, Controller, GameState


class BFSController(Controller):
    def get_action(self, state: GameState) -> Action | None:
        return bfs(state) or any_safe_move(state)


def bfs(state):
    # first move of the shortest path from the head to the food, or None if unreachable
    if state.food is None:
        return None
    walls = set(state.snake[:-1])  # the tail moves out of the way

    q = deque()
    visited = {state.head}
    for action in moves(state):
        cell = step(state, state.head, action)
        if cell not in walls and cell not in visited:
            visited.add(cell)
            q.append((cell, action))

    while q:
        cur_pos, first_action = q.popleft()
        if cur_pos == state.food:
            return first_action
        for action in Action:
            cell = step(state, cur_pos, action)
            if cell not in walls and cell not in visited:
                visited.add(cell)
                q.append((cell, first_action))
    return None


def any_safe_move(state):
    # no path to the food: take any move that doesn't run into the body
    walls = set(state.snake[:-1])
    for action in moves(state):
        if step(state, state.head, action) not in walls:
            return action
    return None


def moves(state):
    # every direction except reversing, which the game ignores
    return [action for action in Action if action != state.direction.opposite]


def step(state, pos, action):
    dx, dy = action.delta
    return (pos[0] + dx) % state.width, (pos[1] + dy) % state.height
