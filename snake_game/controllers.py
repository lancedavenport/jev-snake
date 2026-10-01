"""Pygame-side controllers: keyboard input and a background-thread wrapper.

Every controller subclasses `Controller` from `snake_game.base`.
"""

from __future__ import annotations

import threading
from collections import deque
from concurrent.futures import Future

import pygame

from snake_game.base import Controller
from snake_game.game import Action, GameState


class KeyboardController(Controller):
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


class BackgroundController:
    """Runs a slow controller (e.g. one that calls an API) on a worker thread.

    Turn-based: `ready(state)` starts a request for that state and reports whether
    the answer has arrived; `take()` collects it. The caller only steps the game
    after `take()`, so the answer always matches the current state, and the
    window keeps drawing while the controller thinks.
    """

    def __init__(self, controller: Controller) -> None:
        self._controller = controller
        self._pending: Future[Action | None] | None = None

    def ready(self, state: GameState) -> bool:
        if self._pending is None:
            self._pending = self._start(state)
        return self._pending.done()

    def take(self) -> Action | None:
        """Return the finished answer (re-raising any error from the controller)."""
        assert self._pending is not None and self._pending.done()
        future, self._pending = self._pending, None
        return future.result()

    def reset(self) -> None:
        # Any in-flight request belongs to the old game; its result is simply dropped.
        self._pending = None
        self._controller.reset()

    def _start(self, state: GameState) -> Future[Action | None]:
        future: Future[Action | None] = Future()

        def run() -> None:
            try:
                future.set_result(self._controller.get_action(state))
            except BaseException as e:
                future.set_exception(e)

        # Daemon thread so closing the window never waits on a slow request.
        threading.Thread(target=run, daemon=True).start()
        return future
