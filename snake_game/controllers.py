"""Controllers decide which action the snake takes each tick.

Anything with a `get_action(state)` method can drive the game, so a future
AI/Jev controller only needs to implement the `Controller` protocol.
"""

from __future__ import annotations

from collections import deque
from typing import Protocol

import pygame

from snake_game.game import Action, GameState


class Controller(Protocol):
    def get_action(self, state: GameState) -> Action | None:
        """Return the next action, or None to keep moving in the current direction."""
        ...


class KeyboardController:
    """Human input via arrow keys or WASD."""

    KEY_MAP: dict[int, Action] = {
        pygame.K_UP: Action.UP,
        pygame.K_w: Action.UP,
        pygame.K_DOWN: Action.DOWN,
        pygame.K_s: Action.DOWN,
        pygame.K_LEFT: Action.LEFT,
        pygame.K_a: Action.LEFT,
        pygame.K_RIGHT: Action.RIGHT,
        pygame.K_d: Action.RIGHT,
    }

    def __init__(self) -> None:
        # Buffer a few presses so quick turns (e.g. UP then LEFT within one tick) aren't lost.
        self._queue: deque[Action] = deque(maxlen=3)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Queue a direction key. Returns True if the event was a direction key."""
        if event.type == pygame.KEYDOWN and event.key in self.KEY_MAP:
            self._queue.append(self.KEY_MAP[event.key])
            return True
        return False

    def get_action(self, state: GameState) -> Action | None:
        heading = state.direction
        while self._queue:
            action = self._queue.popleft()
            # Skip presses that wouldn't change anything (same direction or a reversal).
            if action not in (heading, heading.opposite):
                return action
        return None

    def reset(self) -> None:
        self._queue.clear()
