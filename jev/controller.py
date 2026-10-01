"""Jev's controller. Implement `get_action` to decide each move."""

from __future__ import annotations

from snake_game.game import Action, GameState


class JevController:
    def get_action(self, state: GameState) -> Action | None:
        """Called once per game tick. Return an Action, or None to keep going straight."""
        # TODO: Jev's decision logic goes here.
        return None

    def reset(self) -> None:
        """Called when a new game starts. Clear any per-game memory here."""
