"""Base class for everything that drives the snake.

Kept free of Pygame so headless controllers (AI agents, baselines, benchmarks)
can subclass it without pulling in the renderer's dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from snake_game.game import Action, GameState


class Controller(ABC):
    """Chooses the snake's next action from the current state.

    Subclasses must implement `get_action`. Override `reset` only if the
    controller keeps per-game state that needs clearing between games.
    """

    @abstractmethod
    def get_action(self, state: GameState) -> Action | None:
        """Return the next action, or None to keep moving in the current direction."""

    def reset(self) -> None:
        """Called when a new game starts."""
