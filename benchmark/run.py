"""Play controllers headlessly over fixed seeds and save one CSV row per game.

    uv run -m benchmark.run random --games 100
    uv run -m benchmark.run jev --games 5 --max-steps 2000

Game N uses seed (--seed + N) for both the food and the controller, so runs
are reproducible and every agent faces the same food placement.
"""

import argparse
import csv
import logging
import os
import statistics
import time
from datetime import datetime
from pathlib import Path

from snake_game import SnakeGame

RESULTS_DIR = Path(__file__).parent / "results"
FIELDS = ["agent", "seed", "score", "steps", "outcome", "seconds", "ms_per_move"]


def make_random(seed):
    from ablation import RandomController
    return RandomController(seed=seed)


def make_jev(seed):
    from jev import JevController  # imported here so other agents don't need an API key
    return JevController()


AGENTS = {
    "random": make_random,
    "jev": make_jev,
}


def play(agent, seed, width, height, max_steps, starve_limit):
    controller = AGENTS[agent](seed)
    game = SnakeGame(width, height, seed=seed, max_steps_without_food=starve_limit)
    state = game.reset()
    controller.reset()

    start = time.perf_counter()
    while not state.game_over and state.steps < max_steps:
        state = game.step(controller.get_action(state)).state
    seconds = time.perf_counter() - start

    if state.won:
        outcome = "win"
    elif state.starved:
        outcome = "starved"
    elif state.game_over:
        outcome = "died"
    else:
        outcome = "step_limit"  # e.g. an agent that circles forever without eating

    return {
        "agent": agent,
        "seed": seed,
        "score": state.score,
        "steps": state.steps,
        "outcome": outcome,
        "seconds": round(seconds, 3),
        "ms_per_move": round(seconds * 1000 / max(state.steps, 1), 3),
    }


def summarize(rows):
    scores = [r["score"] for r in rows]
    outcomes = {}
    for r in rows:
        outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1

    print(f"\n{rows[0]['agent']}: {len(rows)} games")
    print(f"  score  mean {statistics.mean(scores):.1f}  median {statistics.median(scores):g}"
          f"  min {min(scores)}  max {max(scores)}")
    if len(scores) > 1:
        print(f"         stdev {statistics.stdev(scores):.1f}")
    print(f"  steps  mean {statistics.mean(r['steps'] for r in rows):.0f}")
    print(f"  speed  {statistics.mean(r['ms_per_move'] for r in rows):.2f} ms/move")
    print("  outcomes  " + ", ".join(f"{k} {v}" for k, v in sorted(outcomes.items())))


def main():
    parser = argparse.ArgumentParser(description="Benchmark Snake controllers.")
    parser.add_argument("agent", choices=sorted(AGENTS))
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0, help="seed of the first game")
    parser.add_argument("--width", type=int, default=20)
    parser.add_argument("--height", type=int, default=20)
    parser.add_argument("--max-steps", type=int, default=10_000, help="end a game after this many steps")
    parser.add_argument("--starve-limit", type=int, default=None,
                        help="end a game after this many steps without food (default: width*height, 0 = off)")
    parser.add_argument("--verbose", action="store_true", help="show per-move logs (e.g. Jev's)")
    args = parser.parse_args()
    if args.starve_limit is None:
        args.starve_limit = args.width * args.height
    starve_limit = args.starve_limit or None

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = RESULTS_DIR / f"{args.agent}-{args.width}x{args.height}-{stamp}.csv"

    rows = []
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        try:
            for seed in range(args.seed, args.seed + args.games):
                row = play(args.agent, seed, args.width, args.height, args.max_steps, starve_limit)
                writer.writerow(row)
                f.flush()  # keep finished games if a long (or paid) run is interrupted
                rows.append(row)
                print(f"game {len(rows)}/{args.games} (seed {seed}): "
                      f"score {row['score']}, {row['steps']} steps, {row['outcome']}")
        except KeyboardInterrupt:
            print("\nInterrupted, keeping finished games.")

    if rows:
        summarize(rows)
        print(f"\nSaved {os.path.relpath(path)}")
    else:
        path.unlink()


if __name__ == "__main__":
    main()
