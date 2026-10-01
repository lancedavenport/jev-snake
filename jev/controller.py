import logging
import os
import time

from dotenv import load_dotenv
from typesafe_sdk import Choice, TypeSafeClient, TypeSafeError

from snake_game.base import Controller
from snake_game.game import Action

load_dotenv()

logger = logging.getLogger(__name__)

RULES = (
    "You control a snake on a grid. (0, 0) is the top-left cell; x grows to the right, y grows downward. "
    "The edges wrap around. You die only by moving into your own body. "
    "Moving directly opposite your current direction is ignored. Reach the food without dying."
)

class JevController(Controller):
    def __init__(self, model="jev-1.13.0"):
        api_key = os.getenv("API_KEY")
        if not api_key:
            raise SystemExit("API_KEY is not set; copy .env.example to .env and add your key.")
        self.client = TypeSafeClient(api_key=api_key, model=model)

    def get_action(self, state):
        options = describe_moves(state)
        start = time.perf_counter()
        try:
            action = self.ask(state, options)
        except TypeSafeError as e:
            logger.warning("step %d: API call failed, going straight: %s", state.steps, e)
            return None
        ms = (time.perf_counter() - start) * 1000
        moves = "; ".join(f"{move}={label}" for move, label in options.items())
        logger.info("step %d: %s (score %d, %.0f ms) | options: %s", state.steps, action.value, state.score, ms, moves)
        return action

    def ask(self, state, options):
        instructions = (
            f"{RULES} {describe_food(state)} "
            "Each move says how many empty cells of room you could still reach after it. "
            "Pick the move that gets closer to the food, unless another move has much more room. "
            "Never pick a DEADLY move unless every move is DEADLY."
        )
        response = self.client.system_one(
            state=state.to_dict(),
            questions={"direction": Choice(instructions=instructions, criteria=options)},
        )
        return Action(response.choices["direction"].choice)

def _offset(a, b, size):
    # shortest signed distance on a wrapping axis
    d = (b - a) % size
    return d - size if d > size // 2 else d

def _food_offset(state):
    assert state.food is not None  # only None after the board is full
    hx, hy = state.head
    fx, fy = state.food
    return _offset(hx, fx, state.width), _offset(hy, fy, state.height)

def describe_food(state):
    dx, dy = _food_offset(state)
    parts = []
    if dx:
        parts.append(f"{abs(dx)} cells {'right' if dx > 0 else 'left'}")
    if dy:
        parts.append(f"{abs(dy)} cells {'down' if dy > 0 else 'up'}")
    return "The food is " + " and ".join(parts) + " from your head."

def describe_moves(state):
    # Skip reversals (the game ignores them). Only offer traps if nothing roomier
    # exists, and deadly moves if nothing else is left.
    hx, hy = state.head
    dx, dy = _food_offset(state)
    blocked = set(state.snake[:-1])  # tail moves out of the way
    deadly = {}
    roomy = {}
    traps = {}
    eat = None

    for action in Action:
        if action == state.direction.opposite:
            continue
        mx, my = action.delta
        nxt = ((hx + mx) % state.width, (hy + my) % state.height)
        if nxt in blocked:
            deadly[action.value] = "DEADLY: runs into your own body"
            continue

        if nxt == state.food:
            eat = action.value
        closer = abs(dx - mx) + abs(dy - my) < abs(dx) + abs(dy)
        food = "moves closer to the food" if closer else "moves away from the food"
        room = _room_after_move(state, nxt)
        if room >= len(state.snake):
            roomy[action.value] = f"safe, {food}, {room} cells of room"
        else:
            traps[action.value] = (room, f"TRAP: only {room} cells of room, {food}")

    if roomy:
        return roomy
    if traps:
        most = max(room for room, _ in traps.values())
        # eating always leaves one less cell (the tail stays put), so keep that move too
        return {move: label for move, (room, label) in traps.items() if room == most or move == eat}
    return deadly

def _room_after_move(state, head):
    # flood fill from the new head, treating the body as walls
    eating = head == state.food
    walls = set(state.snake if eating else state.snake[:-1])
    seen = {head}
    stack = [head]
    while stack:
        x, y = stack.pop()
        for mx, my in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            cell = ((x + mx) % state.width, (y + my) % state.height)
            if cell not in walls and cell not in seen:
                seen.add(cell)
                stack.append(cell)
    return len(seen) - 1
