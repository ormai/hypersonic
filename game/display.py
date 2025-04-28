from enum import Enum
from threading import Timer
import pygame
import os

from game.model import Game
from game.entities import CellType, Agent


class Display:
    """Draws the Game on the screen"""

    FRAME_RATE = 60
    CELL_SIZE = 90
    BOMB_SIZE = 72
    SPOT_SIZE = 100
    PLAYER_SIZE = 128
    MAGENTA = (255, 0, 255)
    EXPLOSION_COLOR = (255, 165, 0)  # Orange
    WHITE = (255, 255, 255)
    GRID_OFFSET = (702, 45)
    RES = os.path.join("game", "resources")
    TEXT_BACKGROUND = (0, 0, 0, 230)
    PLAYER_COLORS = [
        (255, 143, 22),
        (255, 29, 92),
        (34, 161, 228),
        (222, 109, 223)
    ]

    def __init__(self, game: Game):
        self.winner_info: str | None = None
        self.game = game

        pygame.init()
        pygame.display.set_caption("Hypersonic")
        self.screen = pygame.display.set_mode((1920, 1080))  # before calling convert()
        self.__load_assets()
        self.start_button = Button("Start", 190, 900, 100, 40, self.medium_font)
        self.pause_button = Button("Stop", 335, 900, 100, 40, self.medium_font)
        self.player_animations = [PlayerAnimation(self, i) for i in range(len(game.agents))]

        # ready in one second
        def set_ready():
            self.ready = True

        self.ready = False
        Timer(1, set_ready).start()

        self.draw(0, True)

    def __load_assets(self):
        try:
            jbm = os.path.join(Display.RES, "JetBrainsMono-Regular.ttf")
            self.font = pygame.font.Font(jbm, 20)
            self.medium_font = pygame.font.Font(jbm, 30)
            self.big_font = pygame.font.Font(jbm, 50)
        except FileNotFoundError:
            self.font = pygame.font.Font(None, 20)
            self.medium_font = pygame.font.Font(None, 30)
            self.big_font = pygame.font.Font(None, 50)

        self.background = pygame.image.load(os.path.join(Display.RES, "background.jpg")).convert()

        game_sheet = pygame.image.load(os.path.join(Display.RES, "game.png")).convert_alpha()
        self.box_sprite = sprite(game_sheet, 264, 139, Display.CELL_SIZE, Display.CELL_SIZE)
        self.bomb_sprites = [sprite(game_sheet, x, y, Display.BOMB_SIZE, Display.BOMB_SIZE)
                             for x, y in ((246, 230), (0, 165), (176, 230), (73, 165))]
        self.player_spots = [
            pygame.image.load(os.path.join(Display.RES, f"spot_player_0{i}.png")).convert_alpha()
            for i in range(1, 5)
        ]

        sheet = pygame.image.load(os.path.join(Display.RES, "players.png")).convert_alpha()
        v_space, h_space, size = 28, 12, Display.PLAYER_SIZE
        self.player_sprites = [
            {
                Agent.State.IDLE: {
                    "down": [sprite(sheet, 2614, 2354 + i * size * i + v_space * i, height=140) for i in range(2)]
                            + [sprite(sheet, size * i + h_space * i, 2666, height=140) for i in range(11)],
                    "up": [sprite(sheet, 3186, 170 + size * i + v_space * i) for i in range(14)],
                    "right": [sprite(sheet, 1504, 19 + size * i + v_space * i) for i in range(10)]
                             + [sprite(sheet, 928 + size * i + h_space * i, 1423) for i in range(4)],
                    "left": [sprite(sheet, 2754, 1100)]
                            + [sprite(sheet, 1914, 1568 + size * i + v_space * i) for i in range(3)]
                            + [sprite(sheet, size * i + h_space * i, 2036) for i in range(9)]
                },
                Agent.State.MOVE: {
                    "down": [sprite(sheet, 5 + size * i + h_space * i, 1714, height=160) for i in range(12)]
                            + [sprite(sheet, 1637, 1082 + size * i + 34 * i, height=160) for i in range(4)],
                    "up": [sprite(sheet, 1640, -14 + size * i + 30 * i, height=160) for i in range(7)]
                          + [sprite(sheet, 145 + size * i + h_space * i, 1552, height=160) for i in range(10)],
                    "right": [sprite(sheet, 1920, 8 + size * i + v_space * i) for i in range(10)]
                             + [sprite(sheet, 850 + size * i + h_space * i, 1880) for i in range(7)],
                    "left": [sprite(sheet, size * i + h_space * i, 1880) for i in range(6)]
                            + [sprite(sheet, 1773, 165 + size * i + v_space * i) for i in range(11)]
                }
            },
            {
                Agent.State.IDLE: {
                    "down": [sprite(sheet, 2194, 12 + size * i + v_space * i, height=140) for i in range(13)]
                            + [sprite(sheet, 2054, 1884 + size * i + v_space * i, height=140) for i in range(2)],
                    "up": [sprite(sheet, 2066, 10 + size * i + v_space * i) for i in range(12)]
                          + [sprite(sheet, 1552 + size * i + h_space * i, 2038) for i in range(3)],
                    "right": [sprite(sheet, 2344, 18 + size * i + v_space * i) for i in range(13)]
                             + [sprite(sheet, 1970 + size * i + h_space * i, 2202) for i in range(2)],
                    "left": [sprite(sheet, size * i + h_space * i, 2190) for i in range(14)]
                            + [sprite(sheet, 2194, 2034)]
                },
                Agent.State.MOVE: {
                    "down": [sprite(sheet, 2104 + i * size + h_space * i, 2338, height=160) for i in range(2)]
                            + [sprite(sheet, 2480, i * size + v_space * i, height=160) for i in range(15)],
                    "up": [sprite(sheet, 2340, 2030 + size * i + i * v_space, height=160) for i in range(2)]
                          + [sprite(sheet, 5 + size * i + h_space * i, 2340, height=160) for i in range(15)],
                    "right": [sprite(sheet, 2252 + i * size + i * h_space, 2500) for i in range(2)]
                             + [sprite(sheet, 2626, 5 + i * size + i * v_space) for i in range(15)],
                    "left": [sprite(sheet, i * size + i * h_space, 2505) for i in range(16)]
                            + [sprite(sheet, 2473, 2349)]
                }
            }
        ]

    def handle(self, event: pygame.event.Event):
        """Handles any interesting event"""
        match event.type:
            case pygame.MOUSEMOTION:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self.start_button.is_hover(
                    event.pos) or self.pause_button.is_hover(event.pos) else pygame.SYSTEM_CURSOR_ARROW)

    def draw(self, delta_time: float, turn_progress: float, paused: bool):
        """Draw grid and all entities, gets called at every frame"""
        self.screen.blit(self.background, (0, 0))

        self.__draw_grid()
        self.__draw_explosions()
        self.__draw_bombs()
        for player_animation in self.player_animations:
            player_animation.draw(turn_progress, paused)
        self.__draw_turn_info(delta_time)
        if self.ready:
            self.start_button.draw(self.screen)
        self.pause_button.draw(self.screen)

        if self.game.turn >= Game.MAX_TURNS:
            if self.winner_info is None:
                self.winner_info = (
                    f"Winner: {max((agent for agent in self.game.agents), key=lambda a: a.boxes_destroyed).name}"
                    if len(set([agent.boxes_destroyed for agent in self.game.agents])) != 1
                    else "Draw")
            self.show_final_message(self.winner_info)

        pygame.display.flip()

    def __draw_turn_info(self):
        left, top, width = 165, 100, 300

        turns_left_box = pygame.Surface((width, 40), pygame.SRCALPHA)
        turns_left_box.fill(Display.TEXT_BACKGROUND)
        turns_surface = self.medium_font.render(f"Rounds left {Game.MAX_TURNS - self.game.turn:3}", True, Display.WHITE)
        turns_left_box.blit(turns_surface,
                            turns_surface.get_rect(center=(width // 2, turns_left_box.get_height() // 2)))
        self.screen.blit(turns_left_box, (left, top))

        box_spacing = 20

        top += box_spacing * 3 + turns_left_box.get_height()

        for i in range(len(self.game.agents)):
            player_surface = pygame.Surface((width, 130), pygame.SRCALPHA)
            player_surface.fill(Display.TEXT_BACKGROUND)

            line_spacing = 5
            top_box_offset = 10
            agent = self.game.agents[i]

            name_surface = self.font.render(agent.name, True, Display.PLAYER_COLORS[i])
            player_surface.blit(name_surface, name_surface.get_rect(topleft=(10, top_box_offset)))
            top_box_offset += name_surface.get_height() + line_spacing + 20

            score_surface = self.font.render(f"Boxes destroyed {agent.boxes_destroyed:>7}", True,
                                             Display.PLAYER_COLORS[i])
            player_surface.blit(score_surface, score_surface.get_rect(topleft=(10, top_box_offset)))
            top_box_offset += score_surface.get_height() + line_spacing

            bombs_surface = self.font.render(f"Bombs left {agent.bombs_left:>10}/1", True, Display.PLAYER_COLORS[i])
            player_surface.blit(bombs_surface, bombs_surface.get_rect(topleft=(10, top_box_offset)))
            top_box_offset += bombs_surface.get_height() + line_spacing

            self.screen.blit(player_surface, (left, top))
            top += player_surface.get_height() + box_spacing

        if __debug__:
            for i, agent in enumerate(self.game.agents):
                top += 40 * i
                self.screen.blit(self.font.render(f"{agent.name} x: {agent.x}, y: {agent.y}", True, Display.MAGENTA,
                                                  Display.TEXT_BACKGROUND), (left, top))
            top += 40
            self.screen.blit(
                self.font.render(f"Boxes left: {sum(row.count(CellType.BOX.value) for row in self.game.grid)}", True,
                                 Display.MAGENTA, Display.TEXT_BACKGROUND), (left, top))
            top += 40
            self.screen.blit(
                self.font.render(f"Frame rate: {1 / delta_time:.0f}", True, Display.MAGENTA, Display.TEXT_BACKGROUND),
                (left, top))

    def __draw_grid(self):
        for r in range(Game.HEIGHT):
            for c in range(Game.WIDTH):
                if self.game.grid[r][c] == CellType.BOX.value:
                    self.screen.blit(self.box_sprite, (c * Display.CELL_SIZE + Display.GRID_OFFSET[0],
                                                       r * Display.CELL_SIZE + Display.GRID_OFFSET[1]))
                    rect = self.screen.blit(self.box_sprite, (c * Display.CELL_SIZE + Display.GRID_OFFSET[0],
                                                              r * Display.CELL_SIZE + Display.GRID_OFFSET[1]))
                        pygame.draw.rect(self.screen, Display.MAGENTA, rect, 1)

    def __draw_bombs(self):
        cell_offset = (Display.CELL_SIZE - Display.BOMB_SIZE) // 2
        for bomb in self.game.bombs:
            if not bomb.exploded:
                self.screen.blit(self.bomb_sprites[bomb.owner_id],
                                 (bomb.x * self.CELL_SIZE + Display.GRID_OFFSET[0] + cell_offset,
                                  bomb.y * self.CELL_SIZE + Display.GRID_OFFSET[1] + cell_offset))

    def __draw_explosions(self):
        for explosion in self.game.explosion_visuals:
            px = explosion.x * self.CELL_SIZE + Display.GRID_OFFSET[0]
            py = explosion.y * self.CELL_SIZE + Display.GRID_OFFSET[1]
            # rect = pygame.Rect(px, py, cell_size, cell_size)
            # Fade effect based on timer
            alpha = max(0, min(255, int(255 * (explosion.timer / explosion.TICK_DURATION))))
            surface = pygame.Surface((Display.CELL_SIZE, Display.CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(surface, (*self.EXPLOSION_COLOR, alpha), surface.get_rect())
            self.screen.blit(surface, (px, py))

    def show_final_message(self, message: str):
        win_surface = self.big_font.render(message, True, (255, 215, 0))
        win_rect = win_surface.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))
        bg_rect = win_rect.inflate(20, 20)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), bg_rect)  # Semi-transparent black bg
        self.screen.blit(win_surface, win_rect)

    @staticmethod
    def cell_to_px(x: int, y: int) -> tuple[int, int]:
        """Translate a pair of cell indexes to screen coordinates in pixels"""
        nx = x * Display.CELL_SIZE + Display.CELL_SIZE // 2 + Display.GRID_OFFSET[0]
        ny = y * Display.CELL_SIZE + Display.CELL_SIZE // 2 + Display.GRID_OFFSET[1]
        return nx, ny


def sprite(sheet: pygame.Surface, x: int, y: int, width=128, height=128) -> pygame.Surface:
    """Get the sprite from the sheet at (x, y)"""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.blit(sheet, (0, 0), (x, y, width, height))
    return surface


def lerp(start: int, end: int, progress: float) -> float:
    """https://en.wikipedia.org/wiki/Linear_interpolation"""
    return start + (end - start) * progress


class PlayerAnimation:
    def __init__(self, display: Display, agent_id: int):
        self.screen = display.screen
        self.spot = display.player_spots[agent_id]
        self.sprites = display.player_sprites[agent_id]
        self.agent = display.game.agents[agent_id]
        self.frame = 0  # one of the loaded image sprites
        self.frame_count = 0
        self.img = self.sprites[self.agent.state][self.agent.direction][self.frame]
        self.font = display.medium_font

        name_text = self.font.render(self.agent.name, True, Display.PLAYER_COLORS[self.agent.id])
        self.name = pygame.Surface((name_text.get_width() + 15, name_text.get_height() + 10), pygame.SRCALPHA)
        self.name.fill(Display.TEXT_BACKGROUND)
        self.name.blit(name_text, name_text.get_rect(center=(self.name.get_width() // 2, self.name.get_height() // 2)))

    def draw(self, turn_progress: float, paused: bool):
        x, y = Display.cell_to_px(self.agent.x, self.agent.y)

        if not paused and self.agent.state == Agent.State.MOVE:
            src_x, src_y = Display.cell_to_px(self.agent.previous_x, self.agent.previous_y)
            x = lerp(src_x, x, turn_progress)
            y = lerp(src_y, y, turn_progress)

        self.frame_count += 1
        speed = Display.FRAME_RATE / len(self.sprites[self.agent.state][self.agent.direction])
        if self.frame_count >= speed:
            self.frame_count = 0
            state = Agent.State.IDLE if paused else self.agent.state
            self.frame = (self.frame + 1) % len(self.sprites[state][self.agent.direction])
            self.img = self.sprites[state][self.agent.direction][self.frame]

        self.screen.blit(self.spot, (x - self.spot.get_width() // 2, y - self.spot.get_height() // 2))
        rect = self.screen.blit(self.img, (x - self.img.get_width() // 2, y - self.img.get_height() // 2))
        if __debug__:
            pygame.draw.rect(self.screen, Display.MAGENTA, rect, 1)

        if paused:
            self.screen.blit(self.name, self.name.get_rect(center=(x, y)))


class Button:
    BACKGROUND = (20, 21, 22)
    HOVER_BACKGROUND = (100, 40, 20)
    CLICK_BACKGROUND = (240, 80, 40)

    def __init__(self, text: str, left: int, top: int, width: int, height: int, font: pygame.font.Font):
        self.text = text
        self.rect = pygame.Rect(left, top, width + 20, height + 10)
        self.text_surface = font.render(self.text, True, Display.WHITE)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
        self.state = Button.State.NORMAL

    def draw(self, screen: pygame.Surface):
        match self.state:
            case Button.State.NORMAL:
                color = Button.BACKGROUND
            case Button.State.HOVER:
                color = Button.HOVER_BACKGROUND
            case Button.State.CLICKED:
                color = Button.CLICK_BACKGROUND
            case _:
                raise ValueError(f"Invalid button state: {self.state}")
        pygame.draw.rect(screen, color, self.rect)
        screen.blit(self.text_surface, self.text_rect)

    def is_clicked(self, pos: tuple[int, int], clicked: bool) -> bool:
        if clicked and self.rect.collidepoint(pos):
            self.state = Button.State.CLICKED
            return True
        self.state = Button.State.NORMAL
        return False

    def is_hover(self, pos: tuple[int, int]) -> bool:
        if self.rect.collidepoint(pos):
            self.state = Button.State.HOVER
            return True
        self.state = Button.State.NORMAL
        return False

    class State(Enum):
        NORMAL = 0
        HOVER = 1
        CLICKED = 2
