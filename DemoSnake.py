"""Python pygame port of the Game01 neon Tetris game."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

import pygame

COLS = 10
ROWS = 20
CELL = 30
BOARD_X = 28
BOARD_Y = 28
PANEL_X = BOARD_X + COLS * CELL + 32
WIDTH = PANEL_X + 238
HEIGHT = BOARD_Y + ROWS * CELL + 28
FPS = 60
BG = (30, 12, 23)
CARD = (50, 22, 39)
BOARD_BG = (22, 12, 24)
CELL_EMPTY = (46, 24, 41)
TEXT = (255, 239, 247)
MUTED = (195, 143, 170)
PINK = (255, 92, 157)
LIGHT_PINK = (255, 157, 196)
LAVENDER_PINK = (220, 142, 255)

SHAPES = [
    ("#ff5c9d", [[1, 1, 1, 1]]),
    ("#ff9dc4", [[1, 1], [1, 1]]),
    ("#ff3d84", [[0, 1, 0], [1, 1, 1]]),
    ("#ff78b2", [[1, 0, 0], [1, 1, 1]]),
    ("#dc8eff", [[0, 0, 1], [1, 1, 1]]),
    ("#f0a6ff", [[0, 1, 1], [1, 1, 0]]),
    ("#ffb3d1", [[1, 1, 0], [0, 1, 1]]),
]
ITEMS = {
    "bomb": ("B", "Bomb: removes one extra row", "#ff78b2"),
    "bonus": ("+", "Line bonus: +500 points", "#ff9dc4"),
    "slow": ("S", "Slow: 8 seconds", "#dc8eff"),
}
HIGH_SCORE_FILE = Path(__file__).with_name("neon_tetris_high_score.json")


def make_board() -> list[list[Optional[dict]]]:
    return [[None for _ in range(COLS)] for _ in range(ROWS)]


def copy_shape(shape: list[list[int]]) -> list[list[int]]:
    return [row[:] for row in shape]


def rotate_shape(shape: list[list[int]]) -> list[list[int]]:
    return [list(row) for row in zip(*shape[::-1])]


def load_high_score() -> int:
    try:
        return int(json.loads(HIGH_SCORE_FILE.read_text(encoding="utf-8")))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return 0


def save_high_score(value: int) -> None:
    HIGH_SCORE_FILE.write_text(json.dumps(value), encoding="utf-8")


def new_piece() -> dict:
    color, shape = random.choice(SHAPES)
    item = None
    if random.random() < 0.20:
        filled = [(x, y) for y, row in enumerate(shape) for x, value in enumerate(row) if value]
        item_type = random.choice(list(ITEMS))
        item = {"type": item_type, "position": random.choice(filled)}
    return {
        "color": color,
        "shape": copy_shape(shape),
        "item": item,
        "x": (COLS - len(shape[0])) // 2,
        "y": 0,
    }


def can_move(board: list[list[Optional[dict]]], piece: dict, dx: int = 0, dy: int = 0, shape: Optional[list[list[int]]] = None) -> bool:
    shape = shape or piece["shape"]
    for y, row in enumerate(shape):
        for x, value in enumerate(row):
            if not value:
                continue
            board_x = piece["x"] + x + dx
            board_y = piece["y"] + y + dy
            if board_x < 0 or board_x >= COLS or board_y < 0 or board_y >= ROWS:
                return False
            if board[board_y][board_x] is not None:
                return False
    return True


def item_at(piece: dict, x: int, y: int) -> Optional[dict]:
    item = piece["item"]
    return item if item and item["position"] == (x, y) else None


def lock_piece(board: list[list[Optional[dict]]], piece: dict) -> None:
    for y, row in enumerate(piece["shape"]):
        for x, value in enumerate(row):
            if value:
                board[piece["y"] + y][piece["x"] + x] = {
                    "color": piece["color"],
                    "item": item_at(piece, x, y),
                }


def clear_lines(board: list[list[Optional[dict]]]) -> tuple[int, list[str]]:
    completed = [row for row in board if all(row)]
    item_types = [cell["item"]["type"] for row in completed for cell in row if cell["item"]]
    board[:] = [row for row in board if not all(row)]
    while len(board) < ROWS:
        board.insert(0, [None for _ in range(COLS)])
    return len(completed), item_types


def text(surface: pygame.Surface, font: pygame.font.Font, value: str, position: tuple[int, int], color: tuple[int, int, int]) -> None:
    surface.blit(font.render(value, True, color), position)


def draw_game(surface: pygame.Surface, fonts: dict, board: list[list[Optional[dict]]], piece: Optional[dict], next_piece: dict, score: int, high_score: int, lines: int, paused: bool, game_over: bool, item_message: str) -> None:
    surface.fill(BG)
    pygame.draw.rect(surface, CARD, (12, 12, WIDTH - 24, HEIGHT - 24))
    text(surface, fonts["title"], "NEON TETRIS", (BOARD_X, 22), TEXT)
    text(surface, fonts["small"], "ARCADE / 01", (BOARD_X, 58), LIGHT_PINK)

    pygame.draw.rect(surface, BOARD_BG, (BOARD_X, BOARD_Y + 48, COLS * CELL, ROWS * CELL))
    for y in range(ROWS):
        for x in range(COLS):
            cell = board[y][x]
            draw_cell(surface, x, y + 1, cell, None)
    if piece:
        for y, row in enumerate(piece["shape"]):
            for x, value in enumerate(row):
                if value:
                    draw_cell(surface, piece["x"] + x, piece["y"] + y + 1, {"color": piece["color"], "item": item_at(piece, x, y)}, None)

    panel_y = BOARD_Y + 52
    draw_panel(surface, fonts, "SCORE", f"{score:06d}", panel_y, PINK)
    draw_panel(surface, fonts, "HIGH SCORE", f"{high_score:06d}", panel_y + 76, PINK)
    draw_panel(surface, fonts, "LEVEL", f"{lines // 10 + 1:02d}", panel_y + 152, LIGHT_PINK)
    draw_panel(surface, fonts, "LINES", f"{lines:03d}", panel_y + 228, LIGHT_PINK)
    text(surface, fonts["small"], "NEXT PIECE", (PANEL_X, panel_y + 315), MUTED)
    for y, row in enumerate(next_piece["shape"]):
        for x, value in enumerate(row):
            if value:
                rect = pygame.Rect(PANEL_X + 45 + x * 18, panel_y + 342 + y * 18, 16, 16)
                pygame.draw.rect(surface, pygame.Color(next_piece["color"]), rect, border_radius=2)
    pygame.draw.rect(surface, (78, 35, 61), (PANEL_X, panel_y + 425, 205, 42), border_radius=2)
    text(surface, fonts["small"], item_message, (PANEL_X + 10, panel_y + 438), LIGHT_PINK)
    text(surface, fonts["small"], "ARROWS MOVE / UP ROTATE", (BOARD_X, HEIGHT - 44), MUTED)
    text(surface, fonts["small"], "SPACE DROP   P PAUSE   R RESTART", (BOARD_X, HEIGHT - 27), MUTED)
    if paused or game_over:
        pygame.draw.rect(surface, (35, 13, 28), (BOARD_X + 4, BOARD_Y + 52, COLS * CELL - 8, ROWS * CELL - 8))
        title = "GAME OVER" if game_over else "PAUSED"
        subtitle = "PRESS R TO RESTART" if game_over else "PRESS P TO RESUME"
        text(surface, fonts["overlay"], title, (BOARD_X + 55, BOARD_Y + 300), LIGHT_PINK)
        text(surface, fonts["small"], subtitle, (BOARD_X + 67, BOARD_Y + 340), TEXT)


def draw_cell(surface: pygame.Surface, x: int, y: int, cell: Optional[dict], _piece: Optional[dict]) -> None:
    rect = pygame.Rect(BOARD_X + x * CELL + 2, BOARD_Y + y * CELL + 2, CELL - 4, CELL - 4)
    if not cell:
        pygame.draw.rect(surface, CELL_EMPTY, rect, border_radius=2)
        return
    color = pygame.Color(cell["color"])
    pygame.draw.rect(surface, color, rect, border_radius=2)
    item = cell["item"]
    if item:
        pygame.draw.circle(surface, BOARD_BG, rect.center, 8)
        font = pygame.font.SysFont("consolas", 13, bold=True)
        symbol = ITEMS[item["type"]][0]
        surface.blit(font.render(symbol, True, color), font.render(symbol, True, color).get_rect(center=rect.center))


def draw_panel(surface: pygame.Surface, fonts: dict, label: str, value: str, y: int, accent: tuple[int, int, int]) -> None:
    pygame.draw.rect(surface, (68, 30, 55), (PANEL_X, y, 205, 62), border_radius=2)
    pygame.draw.rect(surface, accent, (PANEL_X, y, 4, 62))
    text(surface, fonts["small"], label, (PANEL_X + 14, y + 10), MUTED)
    text(surface, fonts["value"], value, (PANEL_X + 14, y + 28), TEXT)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Neon Tetris - DemoSnake")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    fonts = {
        "title": pygame.font.SysFont("consolas", 30, bold=True),
        "overlay": pygame.font.SysFont("consolas", 24, bold=True),
        "value": pygame.font.SysFont("consolas", 21, bold=True),
        "small": pygame.font.SysFont("consolas", 11, bold=True),
    }
    clock = pygame.time.Clock()
    board = make_board()
    current = new_piece()
    upcoming = new_piece()
    score = 0
    lines = 0
    high_score = load_high_score()
    item_message = "ITEMS APPEAR RANDOMLY"
    paused = False
    game_over = False
    last_drop = pygame.time.get_ticks()
    slow_until = 0
    running = True

    while running:
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    board, current, upcoming = make_board(), new_piece(), new_piece()
                    score, lines, paused, game_over = 0, 0, False, False
                    item_message = "ITEMS APPEAR RANDOMLY"
                    last_drop = now
                elif event.key == pygame.K_p and not game_over:
                    paused = not paused
                elif not paused and not game_over:
                    if event.key == pygame.K_LEFT and can_move(board, current, dx=-1): current["x"] -= 1
                    elif event.key == pygame.K_RIGHT and can_move(board, current, dx=1): current["x"] += 1
                    elif event.key == pygame.K_UP:
                        rotated = rotate_shape(current["shape"])
                        for offset in (0, -1, 1, -2, 2):
                            if can_move(board, current, dx=offset, shape=rotated):
                                current["x"] += offset
                                current["shape"] = rotated
                                break
                    elif event.key == pygame.K_DOWN and can_move(board, current, dy=1): current["y"] += 1
                    elif event.key == pygame.K_SPACE:
                        distance = 0
                        while can_move(board, current, dy=1):
                            current["y"] += 1
                            distance += 1
                        score += distance * 2
                        lock_piece(board, current)
                        cleared, item_types = clear_lines(board)
                        lines += cleared
                        score += [0, 100, 300, 500, 800][cleared] * (lines // 10 + 1)
                        if "bonus" in item_types: score += 500
                        if "bomb" in item_types: clear_extra_row(board)
                        if "slow" in item_types: slow_until = now + 8000
                        item_message = item_text(item_types)
                        current, upcoming = upcoming, new_piece()
                        if not can_move(board, current): game_over = True
                        last_drop = now

        delay = max(90, 700 - (lines // 10) * 55)
        if now < slow_until: delay *= 2
        if not paused and not game_over and now - last_drop >= delay:
            if can_move(board, current, dy=1): current["y"] += 1
            else:
                lock_piece(board, current)
                cleared, item_types = clear_lines(board)
                lines += cleared
                score += [0, 100, 300, 500, 800][cleared] * (lines // 10 + 1)
                if "bonus" in item_types: score += 500
                if "bomb" in item_types: clear_extra_row(board)
                if "slow" in item_types: slow_until = now + 8000
                item_message = item_text(item_types)
                current, upcoming = upcoming, new_piece()
                if not can_move(board, current): game_over = True
            last_drop = now

        if score > high_score:
            high_score = score
            save_high_score(high_score)
        draw_game(screen, fonts, board, current, upcoming, score, high_score, lines, paused, game_over, item_message)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


def clear_extra_row(board: list[list[Optional[dict]]]) -> None:
    occupied = next((index for index, row in enumerate(board) if any(row)), None)
    if occupied is not None:
        board.pop(occupied)
        board.insert(0, [None for _ in range(COLS)])


def item_text(item_types: list[str]) -> str:
    if not item_types:
        return "ITEMS APPEAR RANDOMLY"
    return " | ".join(ITEMS[item_type][1] for item_type in item_types)


if __name__ == "__main__":
    main()
