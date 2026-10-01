"""Play Snake with the keyboard.

Rendering runs at RENDER_FPS, but the game advances on a fixed timestep of
TICKS_PER_SECOND, so movement speed is independent of frame rate.
"""

from __future__ import annotations

import pygame

from snake_game.controllers import KeyboardController
from snake_game.game import SnakeGame
from snake_game.renderer import Renderer

GRID_WIDTH = 20
GRID_HEIGHT = 20
TICKS_PER_SECOND = 10
RENDER_FPS = 60
MAX_FRAME_TIME = 0.25  # Avoid a burst of catch-up steps after a stall (e.g. window drag).

RESTART_KEYS = (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN)


def main() -> None:
    pygame.init()
    game = SnakeGame(GRID_WIDTH, GRID_HEIGHT)
    renderer = Renderer(GRID_WIDTH, GRID_HEIGHT)
    controller = KeyboardController()
    clock = pygame.time.Clock()

    step_interval = 1.0 / TICKS_PER_SECOND
    accumulator = 0.0
    state = game.reset()
    high_score = 0
    started = False
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
                    controller.reset()
                    started = False
            elif event.key == pygame.K_p and started:
                paused = not paused
            elif not paused and controller.handle_event(event):
                started = True

        if started and not paused and not state.game_over:
            while accumulator >= step_interval and not state.game_over:
                state, _reward, _done = game.step(controller.get_action(state))
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
