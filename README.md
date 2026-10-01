# jev-snake

A small Snake game in Python + Pygame, played by an AI controller ("Jev").

## About

Just a quick project to work on and get some hands-on exposure to Jev. Claude built the Snake game itself (the game logic, rendering and keyboard controls), and I worked on the Jev side: hooking up the model, writing the prompts and iterating on how it plays.

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
│   ├── base.py              # Controller base class (no Pygame)
│   ├── controllers.py       # KeyboardController, BackgroundController
│   └── renderer.py          # Draws a GameState with Pygame
├── jev/
│   └── controller.py        # JevController: asks the model for each move
├── baselines/               # Comparison agents (RandomController, BFSController)
├── benchmark/
│   ├── run.py               # Headless benchmark: plays N seeded games, writes a CSV
│   └── results/             # One CSV per run
├── .env.example             # Template for Jev's API key
├── LICENSE
└── requirements.txt
```

The game logic in `game.py` doesn't import Pygame, so it can run headless and as fast as you like. The renderer only reads state, and controllers only choose actions.

Movement is deterministic: `main.py` renders at 60 FPS but advances the game on a fixed timestep (10 ticks/second). One `step()` = the snake moves exactly one cell. Pass `seed=` to `SnakeGame` for reproducible food placement.

To change the board size, edit `GRID_WIDTH` and `GRID_HEIGHT` in `main.py` (minimum 5×5). For big boards, also pass a smaller `cell_size` to `Renderer` so the window fits on screen.

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

**Starvation limit (optional):** `SnakeGame(..., max_steps_without_food=N)` ends the game (with `state.starved = True` and a `-1` reward) when the snake goes `N` steps without eating. It's off by default, so keyboard games are unchanged; Jev and the benchmark turn it on so an agent stuck in a loop can't play forever.

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
| `starved`    | Whether it ended by the starvation limit      |

`state.to_dict()` gives a plain JSON-serializable version.

**Rewards** (constants in `game.py`): `+1` for eating food, `-1` for dying, `0` otherwise.

## Plugging in Jev (AI controller)

Jev lives in its own package, `jev/`, next to `snake_game/`. `jev` imports from `snake_game`, and `snake_game` never imports `jev`, so the game stays independent of the AI and its dependencies.

### How it works

`JevController` in `jev/controller.py` subclasses `Controller` from `snake_game/base.py`: the game calls `get_action(state)` once per move, and `reset()` when a new game starts. Each move:

1. `describe_moves` works out the moves worth considering and labels each one (see below).
2. `ask` sends the game state, the rules and where the food is to the TypeSafe API (`system_one` with a `Choice` question, model `jev-1.13.0`), with the labeled moves as the choices.
3. The model's pick comes back as an `Action`. If the API call fails, the snake keeps going straight.

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

### Move labels

Jev only sees moves worth considering. Each is labeled with whether it gets closer to the food and how many empty cells the snake could still reach afterwards (a flood fill):

```text
LEFT=safe, moves closer to the food, 372 cells of room
UP=TRAP: only 6 cells of room, moves away from the food
```

Reversals are never offered (the game ignores them). Moves into its own body (`DEADLY`) or into a pocket smaller than the snake (`TRAP`) are left out whenever a better move exists.

### Running Jev

There are two ways to run it:

1. **Watch Jev play:** `uv run main.py --jev`. The game starts immediately and ignores direction keys (P, R and Esc still work). Jev plays **turn-based**: `get_action` runs on a background thread (`BackgroundController` in `snake_game/controllers.py`), and the game steps only once Jev has answered for the current state, at most 10 steps per second. The window keeps drawing at 60 FPS while Jev thinks, and Jev never acts on an outdated board.

   Each move is logged to the terminal with its latency and the options Jev was given. Failed API calls are logged as warnings (the snake goes straight on a failure):

   ```text
   INFO jev.controller: step 12: LEFT (score 2, 430 ms) | options: UP=safe, moves away from the food, 372 cells of room; LEFT=safe, moves closer to the food, 372 cells of room
   WARNING jev.controller: step 13: API call failed, going straight: ...
   INFO root: Game over: score 7 after 94 steps
   ```

   The SDK also logs each request (`typesafe_sdk` logger), including retries.

   If Jev goes `JEV_MAX_STEPS_WITHOUT_FOOD` steps without eating (default: one step per board cell, set in `main.py`), the game ends as **Starved** instead of looping forever.
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

## Benchmark

`benchmark/run.py` plays an agent headlessly (no window) over a fixed set of seeds and writes one CSV row per game to `benchmark/results/`:

```bash
uv run -m benchmark.run random --games 1000
uv run -m benchmark.run jev --games 5 --max-steps 2000   # makes one API call per move
```

Game N uses seed `--seed + N` (default 0) for both the food and the agent, so every agent faces the same food placement and runs are reproducible. A game ends when the snake dies, fills the board, goes `--starve-limit` steps without eating (default: width × height, `0` turns it off, recorded as `starved`), or hits `--max-steps` (default 10,000, recorded as `step_limit`). Each row has the score, steps, outcome and time per move, and a summary prints at the end. Ctrl+C stops early and keeps the finished games.

To add an agent, subclass `Controller` and register a factory in `AGENTS` in `benchmark/run.py`.

## License

MIT. See [LICENSE](LICENSE).
