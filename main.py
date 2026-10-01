"""Play Snake with the keyboard, or watch Jev play with `python main.py --jev`.

Rendering runs at RENDER_FPS, but the game advances on a fixed timestep of
TICKS_PER_SECOND, so movement speed is independent of frame rate. Jev plays
turn-based: its API calls run on a background thread and the game steps once
each answer arrives (never faster than TICKS_PER_SECOND), so the window stays smooth.
"""

from __future__ import annotations

import argparse
import logging

import pygame

from jev import JevController
from snake_game.controllers import BackgroundController, KeyboardController
from snake_game.game import SnakeGame
from snake_game.renderer import Renderer

GRID_WIDTH = 20
GRID_HEIGHT = 20
TICKS_PER_SECOND = 10
RENDER_FPS = 60
MAX_FRAME_TIME = 0.25  # Avoid a burst of catch-up steps after a stall (e.g. window drag).

RESTART_KEYS = (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN)


def main() -> None:
    parser = argparse.ArgumentParser(description="Play Snake.")
    parser.add_argument("--jev", action="store_true", help="let the Jev controller play")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    pygame.init()
    game = SnakeGame(GRID_WIDTH, GRID_HEIGHT)
    renderer = Renderer(GRID_WIDTH, GRID_HEIGHT)
    keyboard = KeyboardController()
    jev = BackgroundController(JevController()) if args.jev else None
    clock = pygame.time.Clock()

    step_interval = 1.0 / TICKS_PER_SECOND
    accumulator = 0.0
    state = game.reset()
    high_score = 0
    started = args.jev  # Jev starts immediately; humans start on their first key press.
    paused = False
    running = True

    while running:
        accumulator += min(clock.tick(RENDER_FPS) / 1000.0, MAX_FRAME_TIME)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type != pygame.KEYDOWN:
                continue
            elif event.key == pygame.K_ESCAPE:
                running = False
            elif state.game_over:
                if event.key in RESTART_KEYS:
                    state = game.reset()
                    keyboard.reset()
                    if jev is not None:
                        jev.reset()
                    started = args.jev
            elif event.key == pygame.K_p and started:
                paused = not paused
            elif not paused and not args.jev and keyboard.handle_event(event):
                started = True

        if started and not paused and not state.game_over:
            if jev is not None:
                # Turn-based: don't bank time while waiting, so a slow answer never causes catch-up steps.
                accumulator = min(accumulator, step_interval)
                if jev.ready(state) and accumulator >= step_interval:
                    state = game.step(jev.take()).state
                    accumulator -= step_interval
                    if state.game_over:
                        logging.info("Game over: score %d after %d steps", state.score, state.steps)
            else:
                while accumulator >= step_interval and not state.game_over:
                    state = game.step(keyboard.get_action(state)).state
                    accumulator -= step_interval
        else:
            accumulator = 0.0

        high_score = max(high_score, state.score)

        message, hint = None, None
        if state.game_over:
            message = "You Win!" if state.won else "Game Over"
            hint = f"Score {state.score}  -  press R to play again"
        elif paused:
            message, hint = "Paused", "Press P to resume"
        elif not started:
            message, hint = "Snake", "Arrow keys / WASD to start  -  P to pause"

        renderer.draw(state, high_score, message, hint)

    pygame.quit()


if __name__ == "__main__":
    main()
