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
        start = time.perf_counter()
        try:
            action = self.ask(state)
        except TypeSafeError as e:
            # Failed calls fall back to going straight; log them so they don't look like bad decisions.
            logger.warning("step %d: API call failed, going straight: %s", state.steps, e)
            return None
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "step %d: %s (score %d, %.0f ms)",
            state.steps, action.value if action else "NONE", state.score, elapsed_ms,
        )
        return action

    def reset(self) -> None:
        """Called when a new game starts. Clear any per-game memory here."""

    def ask(self, curr_state: GameState) -> Action | None:
        r = self.client.system_one(
            state=curr_state.to_dict(),
            questions={
                "direction": Choice(
                    instructions=RULES + " Which direction should the Snake go?",
                    criteria={
                          "UP": "Move toward the top of the screen (y - 1)",
                          "DOWN": "Move toward the bottom of the screen (y + 1)",
                          "LEFT": "Move toward the left of the screen (x - 1)",
                          "RIGHT": "Move toward the right of the screen (x + 1)",
                          "NONE": "Keep moving in the current direction",
                    }
                )
            }
        )
        choice = r.choices["direction"].choice
        return None if choice == "NONE" else Action(choice)
