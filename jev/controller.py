"""Jev's controller. Implement `get_action` to decide each move."""

from snake_game.game import Action, GameState
from typesafe_sdk import TypeSafeClient, Choice, TypeSafeError
import logging
import os
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

RULES = (
      "You control a snake on a grid. (0, 0) is the top-left cell; x grows to the right, y grows downward. "
      "The edges wrap around. You die only by moving into your own body. "
      "Moving directly opposite your current direction is ignored. Reach the food without dying."
  )


class JevController:
    def __init__(self, model: str | None = "jev-1.13.0") -> None:
        api_key = os.getenv("API_KEY")
        if not api_key:
            raise SystemExit("API_KEY is not set; copy .env.example to .env and add your key.")
        self.client = TypeSafeClient(api_key=api_key, model=model)

    def get_action(self, state: GameState) -> Action | None:
        """Called once per game tick. Return an Action, or None to keep going straight."""
        options = describe_moves(state)
        start = time.perf_counter()
        try:
            action = self.ask(state, options)
        except TypeSafeError as e:
            # Failed calls fall back to going straight; log them so they don't look like bad decisions.
            logger.warning("step %d: API call failed, going straight: %s", state.steps, e)
            return None
        elapsed_ms = (time.perf_counter() - start) * 1000
        picked = action.value if action else "NONE"
        # Warn when Jev ignores its labels, so those moves stand out in the log.
        ignored_labels = options.get(picked, "").startswith("DEADLY") and any(
            not label.startswith("DEADLY") for label in options.values()
        )
        logger.log(
            logging.WARNING if ignored_labels else logging.INFO,
            "step %d: %s%s (score %d, %.0f ms) | options: %s",
            state.steps, picked, " (DEADLY, a safe move was available)" if ignored_labels else "",
            state.score, elapsed_ms, "; ".join(f"{move}={label}" for move, label in options.items()),
        )
        return action

    def reset(self) -> None:
        """Called when a new game starts. Clear any per-game memory here."""

    def ask(self, curr_state: GameState, options: dict[str, str]) -> Action | None:
        r = self.client.system_one(
            state=curr_state.to_dict(),
            questions={
                "direction": Choice(
                    instructions=(
                        RULES + " " + describe_food(curr_state)
                        + " Pick the move that is safe and gets closer to the food."
                        " Never pick a DEADLY move unless every move is DEADLY."
                    ),
                    criteria=options,
                )
            }
        )
        return Action(r.choices["direction"].choice)


def _offset(a: int, b: int, size: int) -> int:
    """Shortest signed distance from a to b on a wrapping axis."""
    d = (b - a) % size
    return d - size if d > size // 2 else d


def _food_offset(state: GameState) -> tuple[int, int]:
    """(dx, dy) from the head to the food, the short way across wrapping edges."""
    # Food is only None once the snake fills the board, and Jev is never asked after the game ends.
    assert state.food is not None, "no food: the game is already over"
    hx, hy = state.head
    fx, fy = state.food
    return _offset(hx, fx, state.width), _offset(hy, fy, state.height)


def describe_food(state: GameState) -> str:
    """Where the food is relative to the head, e.g. "The food is 9 cells right and 4 cells down." """
    dx, dy = _food_offset(state)
    parts = []
    if dx:
        parts.append(f"{abs(dx)} cells {'right' if dx > 0 else 'left'}")
    if dy:
        parts.append(f"{abs(dy)} cells {'down' if dy > 0 else 'up'}")
    return "The food is " + " and ".join(parts) + " from your head."


def describe_moves(state: GameState) -> dict[str, str]:
    """The legal moves this turn (no reversal), each labeled safe/DEADLY and closer/away from food."""
    hx, hy = state.head
    dx, dy = _food_offset(state)
    blocked = set(state.snake[:-1])  # the tail moves out of the way
    options = {}
    for action in Action:
        if action == state.direction.opposite:
            continue  # reversing is ignored by the game, so don't offer it
        mx, my = action.delta
        nxt = ((hx + mx) % state.width, (hy + my) % state.height)
        closer = abs(dx - mx) + abs(dy - my) < abs(dx) + abs(dy)
        if nxt in blocked:
            options[action.value] = "DEADLY: runs into your own body"
        else:
            options[action.value] = "safe, " + ("moves closer to the food" if closer else "moves away from the food")
    return options
