"""Pygame rendering. Reads a GameState and draws it; never mutates the game."""

from __future__ import annotations

import pygame

from snake_game.game import Action, GameState

Color = tuple[int, int, int]

BACKGROUND: Color = (18, 20, 28)
CELL_LIGHT: Color = (30, 34, 46)
CELL_DARK: Color = (26, 30, 41)
SNAKE_HEAD: Color = (120, 230, 140)
SNAKE_TAIL: Color = (36, 120, 70)
FOOD: Color = (240, 84, 90)
EYE: Color = (18, 20, 28)
TEXT: Color = (230, 232, 240)
TEXT_DIM: Color = (140, 146, 165)

HEADER_HEIGHT = 48
PADDING = 12


def _lerp_color(a: Color, b: Color, t: float) -> Color:
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


class Renderer:
    def __init__(self, grid_width: int, grid_height: int, cell_size: int = 28) -> None:
        self.cell = cell_size
        self.board_rect = pygame.Rect(
            PADDING, HEADER_HEIGHT, grid_width * cell_size, grid_height * cell_size
        )
        size = (self.board_rect.width + 2 * PADDING, self.board_rect.bottom + PADDING)
        self.screen = pygame.display.set_mode(size)
        pygame.display.set_caption("Jev Snake")
        self.font = pygame.font.Font(None, 32)
        self.big_font = pygame.font.Font(None, 64)
        self.small_font = pygame.font.Font(None, 26)
        self._board = self._make_board_surface(grid_width, grid_height)

    def draw(
        self,
        state: GameState,
        high_score: int = 0,
        message: str | None = None,
        hint: str | None = None,
    ) -> None:
        """Draw a full frame. `message`/`hint` show a centered overlay (pause, game over, ...)."""
        self.screen.fill(BACKGROUND)
        self._draw_header(state, high_score)
        self.screen.blit(self._board, self.board_rect)
        if state.food is not None:
            self._draw_food(state.food)
        self._draw_snake(state)
        if message:
            self._draw_overlay(message, hint)
        pygame.display.flip()

    def _cell_rect(self, x: int, y: int) -> pygame.Rect:
        return pygame.Rect(
            self.board_rect.x + x * self.cell, self.board_rect.y + y * self.cell, self.cell, self.cell
        )

    def _make_board_surface(self, w: int, h: int) -> pygame.Surface:
        # Checkerboard is static, so draw it once.
        surface = pygame.Surface((w * self.cell, h * self.cell))
        for y in range(h):
            for x in range(w):
                color = CELL_LIGHT if (x + y) % 2 == 0 else CELL_DARK
                surface.fill(color, (x * self.cell, y * self.cell, self.cell, self.cell))
        return surface

    def _draw_header(self, state: GameState, high_score: int) -> None:
        score = self.font.render(f"Score: {state.score}", True, TEXT)
        best = self.font.render(f"Best: {high_score}", True, TEXT_DIM)
        y = (HEADER_HEIGHT - score.get_height()) // 2
        self.screen.blit(score, (PADDING, y))
        self.screen.blit(best, (self.screen.get_width() - PADDING - best.get_width(), y))

    def _draw_food(self, pos: tuple[int, int]) -> None:
        rect = self._cell_rect(*pos)
        pygame.draw.circle(self.screen, FOOD, rect.center, self.cell * 0.36)

    def _draw_snake(self, state: GameState) -> None:
        n = len(state.snake)
        inset = max(1, self.cell // 12)
        # Draw tail-to-head so the head is always on top.
        for i in range(n - 1, -1, -1):
            t = i / max(1, n - 1)
            color = _lerp_color(SNAKE_HEAD, SNAKE_TAIL, t)
            rect = self._cell_rect(*state.snake[i]).inflate(-2 * inset, -2 * inset)
            pygame.draw.rect(self.screen, color, rect, border_radius=self.cell // 4)
        self._draw_eyes(state)

    def _draw_eyes(self, state: GameState) -> None:
        rect = self._cell_rect(*state.head)
        cx, cy = rect.center
        dx, dy = state.direction.delta
        forward = self.cell * 0.18
        side = self.cell * 0.2
        # Perpendicular offset places the two eyes side by side relative to heading.
        px, py = (side, 0) if state.direction in (Action.UP, Action.DOWN) else (0, side)
        radius = max(2, self.cell // 9)
        for s in (-1, 1):
            center = (cx + dx * forward + s * px, cy + dy * forward + s * py)
            pygame.draw.circle(self.screen, EYE, center, radius)

    def _draw_overlay(self, message: str, hint: str | None) -> None:
        shade = pygame.Surface(self.board_rect.size, pygame.SRCALPHA)
        shade.fill((10, 12, 18, 170))
        self.screen.blit(shade, self.board_rect)

        title = self.big_font.render(message, True, TEXT)
        center = self.board_rect.center
        title_pos = title.get_rect(center=(center[0], center[1] - (16 if hint else 0)))
        self.screen.blit(title, title_pos)
        if hint:
            sub = self.small_font.render(hint, True, TEXT_DIM)
            self.screen.blit(sub, sub.get_rect(center=(center[0], title_pos.bottom + 22)))
