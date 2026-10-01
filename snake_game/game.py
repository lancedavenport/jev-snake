"""Core Snake game logic.

This module has no Pygame dependency, so the game can run headless
(e.g. thousands of games per second for an AI) or be driven by any front end.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, NamedTuple

Position = tuple[int, int]  # (x, y) grid coordinates; (0, 0) is the top-left cell.

REWARD_FOOD = 1.0
REWARD_DEATH = -1.0
REWARD_STEP = 0.0


class Action(str, Enum):
    """A movement direction. Also used as the snake's current heading."""

    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    @property
    def delta(self) -> Position:
        return _DELTAS[self]

    @property
    def opposite(self) -> Action:
        return _OPPOSITES[self]


_DELTAS: dict[Action, Position] = {
    Action.UP: (0, -1),
    Action.DOWN: (0, 1),
    Action.LEFT: (-1, 0),
    Action.RIGHT: (1, 0),
}
_OPPOSITES: dict[Action, Action] = {
    Action.UP: Action.DOWN,
    Action.DOWN: Action.UP,
    Action.LEFT: Action.RIGHT,
    Action.RIGHT: Action.LEFT,
}


@dataclass(frozen=True)
class GameState:
    """An immutable snapshot of the game, safe to hand to a controller."""

    width: int
    height: int
    snake: tuple[Position, ...]  # Head first, tail last.
    food: Position | None  # None only when the snake fills the whole board.
    direction: Action
    score: int
    steps: int
    game_over: bool

    @property
    def head(self) -> Position:
        return self.snake[0]

    @property
    def body(self) -> tuple[Position, ...]:
        """Snake segments excluding the head."""
        return self.snake[1:]

    @property
    def won(self) -> bool:
        return len(self.snake) == self.width * self.height

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-serializable representation."""
        return {
            "width": self.width,
            "height": self.height,
            "head": list(self.head),
            "body": [list(p) for p in self.body],
            "food": list(self.food) if self.food else None,
            "direction": self.direction.value,
            "score": self.score,
            "steps": self.steps,
            "game_over": self.game_over,
        }


class StepResult(NamedTuple):
    state: GameState
    reward: float
    done: bool


class SnakeGame:
    """Grid-based Snake. One call to `step()` moves the snake exactly one cell.

    The board edges wrap around, so the only way to die is hitting yourself.
    """

    def __init__(self, width: int = 20, height: int = 20, seed: int | None = None) -> None:
        if width < 5 or height < 5:
            raise ValueError("Board must be at least 5x5.")
        self.width = width
        self.height = height
        self._rng = random.Random(seed)
        self.reset()

    def reset(self) -> GameState:
        """Start a new game and return its initial state."""
        cx, cy = self.width // 2, self.height // 2
        self._snake: deque[Position] = deque([(cx, cy), (cx - 1, cy), (cx - 2, cy)])
        self._direction = Action.RIGHT
        self._score = 0
        self._steps = 0
        self._game_over = False
        self._food = self._spawn_food()
        return self.get_state()

    def get_state(self) -> GameState:
        return GameState(
            width=self.width,
            height=self.height,
            snake=tuple(self._snake),
            food=self._food,
            direction=self._direction,
            score=self._score,
            steps=self._steps,
            game_over=self._game_over,
        )

    def step(self, action: Action | str | None = None) -> StepResult:
        """Advance one tick.

        `action` may be an Action, its string name ("UP", ...), or None to keep
        the current direction. Reversing straight into the neck is ignored.
        """
        if self._game_over:
            return StepResult(self.get_state(), 0.0, True)

        if action is not None:
            action = Action(action)
            if action != self._direction.opposite:
                self._direction = action

        self._steps += 1
        dx, dy = self._direction.delta
        hx, hy = self._snake[0]
        # Edges wrap around: leaving one side re-enters on the opposite side.
        new_head = ((hx + dx) % self.width, (hy + dy) % self.height)
        eating = new_head == self._food

        # The tail vacates its cell this tick unless the snake is growing,
        # so moving into the current tail cell is legal.
        blocking = list(self._snake) if eating else list(self._snake)[:-1]
        if new_head in blocking:
            self._game_over = True
            return StepResult(self.get_state(), REWARD_DEATH, True)

        self._snake.appendleft(new_head)
        reward = REWARD_STEP
        if eating:
            self._score += 1
            reward = REWARD_FOOD
            self._food = self._spawn_food()
            if self._food is None:  # Board is full: the player has won.
                self._game_over = True
        else:
            self._snake.pop()

        return StepResult(self.get_state(), reward, self._game_over)

    def _spawn_food(self) -> Position | None:
        occupied = set(self._snake)
        free = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in occupied
        ]
        return self._rng.choice(free) if free else None
