# jev-snake

A small, clean Snake game in Python + Pygame, built so an AI controller ("Jev") can be plugged in later.

## Setup

Requires Python 3.10+. With [uv](https://docs.astral.sh/uv/):

```bash
uv venv
uv pip install -r requirements.txt
```

Without uv: `python3 -m venv .venv`, activate it, then `pip install -r requirements.txt`.

Dependencies:

- [`pygame-ce`](https://pyga.me/): the maintained fork of Pygame. You still write `import pygame`. Upstream `pygame` 2.6.1 has a broken font module on Python 3.14.
- `typesafe-sdk`: the model API Jev uses to pick moves.
- `python-dotenv`: loads Jev's API key from `.env`.

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
├── jev/
│   └── controller.py        # JevController: the AI's get_action (stub for now)
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

Jev lives in its own package, `jev/`, next to `snake_game/`. `jev` imports from `snake_game`, and `snake_game` never imports `jev`, so the game stays independent of the AI and its dependencies.

Fill in `get_action` in `jev/controller.py`:

```python
class JevController:
    def get_action(self, state: GameState) -> Action | None:
        # Decide using state.head, state.body, state.food, state.direction, ...
        return Action.UP

    def reset(self) -> None:
        # Clear any per-game memory.
        ...
```

It follows the `Controller` protocol in `snake_game/controllers.py`. Until you implement it, it returns `None`, so the snake just goes straight.

### API key

Jev calls the TypeSafe API, which needs an API key. Copy the example env file and fill in your key:

```bash
cp .env.example .env
```

```bash
# .env
API_KEY=your-key-here
```

`jev/controller.py` loads `.env` with `python-dotenv` when it's imported, then reads the key with `os.getenv("API_KEY")`. `.env` is git-ignored, so the key never gets committed; `.env.example` is the template you commit. The keyboard game doesn't need a key.

### Running Jev

There are two ways to run it:

1. **Watch Jev play:** `uv run main.py --jev`. The game starts immediately and ignores direction keys (P, R and Esc still work). Jev plays **turn-based**: `get_action` runs on a background thread (`BackgroundController` in `snake_game/controllers.py`), and the game steps only once Jev has answered for the current state, at most 10 steps per second. The window keeps drawing at 60 FPS while Jev thinks, and Jev never acts on an outdated board.

   Each move is logged to the terminal with its latency, and failed API calls are logged as warnings (the snake goes straight on a failure):

   ```text
   INFO jev.controller: step 12: LEFT (score 2, 430 ms)
   WARNING jev.controller: step 13: API call failed, going straight: ...
   INFO root: Game over: score 7 after 94 steps
   ```

   The SDK also logs each request (`typesafe_sdk` logger), including retries.
2. **Headless / fast runs:** skip Pygame entirely and drive `SnakeGame` directly:

   ```python
   from jev import JevController
   from snake_game import SnakeGame

   game = SnakeGame()
   jev = JevController()
   state = game.reset()
   while not state.game_over:
       state, reward, done = game.step(jev.get_action(state))
   print("Final score:", state.score)
   ```
