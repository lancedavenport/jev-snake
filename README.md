# jev-snake

A small, clean Snake game in Python + Pygame, built so an AI controller ("Jev") can be plugged in later.

## Setup

Requires Python 3.10+. With [uv](https://docs.astral.sh/uv/):

```bash
uv venv
uv pip install -r requirements.txt
```

Without uv: `python3 -m venv .venv`, activate it, then `pip install -r requirements.txt`.

The only dependency is [`pygame-ce`](https://pyga.me/), the maintained fork of Pygame. You still write `import pygame`. Upstream `pygame` 2.6.1 has a broken font module on Python 3.14.

## Run

```bash
uv run main.py
```

(Or `python main.py` with `.venv` activated.)

| Key              | Action             |
| ---------------- | ------------------ |
| Arrow keys / WASD | Move (first press starts the game) |
| P                | Pause / resume     |
| R / Space / Enter | Restart after game over |
| Esc              | Quit               |

## Project layout

```text
jev-snake/
├── main.py                  # Game loop: input, fixed-timestep updates, rendering
├── snake_game/
│   ├── game.py              # Pure game logic (no Pygame) + reset/get_state/step API
│   ├── controllers.py       # Controller protocol + KeyboardController
│   └── renderer.py          # Draws a GameState with Pygame
└── requirements.txt
```

The game logic in `game.py` doesn't import Pygame, so it can run headless and as fast as you like. The renderer only reads state, and controllers only choose actions.

Movement is deterministic: `main.py` renders at 60 FPS but advances the game on a fixed timestep (10 ticks/second). One `step()` = the snake moves exactly one cell. Pass `seed=` to `SnakeGame` for reproducible food placement.

## Game API

```python
from snake_game import SnakeGame, Action

game = SnakeGame(width=20, height=20, seed=42)
state = game.reset()                              # -> GameState
state = game.get_state()                          # -> GameState
state, reward, done = game.step(Action.UP)        # also accepts "UP" or None (keep going)
```

**Actions:** `UP`, `DOWN`, `LEFT`, `RIGHT`. Reversing directly into the snake's neck is ignored.

**Edges wrap around:** moving off one side brings the snake back on the opposite side, so the only way to die is running into yourself.

**`GameState`** (immutable):

| Field        | Description                                   |
| ------------ | --------------------------------------------- |
| `head`       | `(x, y)` of the head; `(0, 0)` is top-left    |
| `snake`      | All segments, head first                      |
| `body`       | Segments excluding the head                   |
| `food`       | `(x, y)` of the food (`None` if board is full) |
| `direction`  | Current heading (`Action`)                    |
| `width`, `height` | Board size in cells                     |
| `score`      | Food eaten                                    |
| `steps`      | Ticks played this game                        |
| `game_over`  | Whether the game has ended                    |

`state.to_dict()` gives a plain JSON-serializable version.

**Rewards** (constants in `game.py`): `+1` for eating food, `-1` for dying, `0` otherwise.

## Plugging in Jev (AI controller)

A controller is anything with a `get_action(state)` method (see the `Controller` protocol in `snake_game/controllers.py`):

```python
from snake_game import Action, GameState

class JevController:
    def get_action(self, state: GameState) -> Action | None:
        # Decide using state.head, state.body, state.food, state.direction, ...
        return Action.UP
```

There are two places to connect it:

1. **Watch Jev play** — in `main.py`, replace `KeyboardController()` with your controller. The loop already calls `controller.get_action(state)` once per game tick. (You'll also want to set `started = True` so it doesn't wait for a key press.)
2. **Headless / fast runs** — skip Pygame entirely and drive `SnakeGame` directly:

   ```python
   game = SnakeGame()
   jev = JevController()
   state = game.reset()
   while not state.game_over:
       state, reward, done = game.step(jev.get_action(state))
   print("Final score:", state.score)
   ```
