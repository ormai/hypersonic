from enum import Enum
import pygame
import os

from game.model import Game
from game.enums import CellType


class Display:
    CELL_SIZE = 90
    BOMB_SIZE = 72
    SPOT_SIZE = 100
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
        pygame.init()
        pygame.display.set_caption("Hypersonic")

        self.winner_info: str | None = None

        self.game = game
        try:
            jbm = os.path.join(Display.RES, "JetBrainsMono-Regular.ttf")
            self.font = pygame.font.Font(jbm, 20)
            self.medium_font = pygame.font.Font(jbm, 30)
            self.big_font = pygame.font.Font(jbm, 50)
        except FileNotFoundError:
            self.font = pygame.font.Font(None, 20)
            self.medium_font = pygame.font.Font(None, 30)
            self.big_font = pygame.font.Font(None, 50)
        self.text_height = self.font.size("A")[1]

        self.screen = pygame.display.set_mode((1920, 1080))  # declared before calling convert()

        cell = pygame.Surface((Display.CELL_SIZE, Display.CELL_SIZE), pygame.SRCALPHA)

        game_sheet = pygame.image.load(os.path.join(Display.RES, "game.png")).convert_alpha()
        self.box_sprite = cell.copy()
        self.box_sprite.blit(game_sheet, (0, 0), (264, 139, Display.CELL_SIZE, Display.CELL_SIZE))
        self.bomb_sprites = tuple(cell.copy() for _ in range(4))
        for bomb_sprite, pos in zip(self.bomb_sprites, ((246, 230), (0, 165), (176, 230), (73, 165))):
            bomb_sprite.blit(game_sheet, (0, 0), (*pos, Display.BOMB_SIZE, Display.BOMB_SIZE))

        self.player_spots = [
            pygame.image.load(os.path.join(Display.RES, f"spot_player_0{i}.png")).convert_alpha()
            for i in range(1, 5)
        ]

        self.start_button = Button("Start", 190, 900, 100, 40, self.medium_font)
        self.pause_button = Button("Pause", 335, 900, 100, 40, self.medium_font)

        self.background = pygame.image.load(os.path.join(Display.RES, "background.jpg")).convert()
        self.draw()

    def draw(self):
        """Draw grid and all entities"""
        self.screen.blit(self.background, (0, 0))

        self.__draw_grid()
        self.__draw_explosions()
        self.__draw_bombs()
        self.__draw_agents()
        self.__draw_turn_info()
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

    def __draw_grid(self):
        for r in range(Game.HEIGHT):
            for c in range(Game.WIDTH):
                if self.game.grid[r][c] == CellType.BOX.value:
                    self.screen.blit(self.box_sprite, (c * Display.CELL_SIZE + Display.GRID_OFFSET[0],
                                                       r * Display.CELL_SIZE + Display.GRID_OFFSET[1]))

    def __draw_agents(self):
        for agent in self.game.agents:
            if agent.is_alive:
                # TODO: display agent message

                px = agent.x * Display.CELL_SIZE + Display.CELL_SIZE // 2 + Display.GRID_OFFSET[0]
                py = agent.y * Display.CELL_SIZE + Display.CELL_SIZE // 2 + Display.GRID_OFFSET[1]

                self.screen.blit(self.player_spots[agent.id],
                                 (px - Display.SPOT_SIZE // 2, py - Display.SPOT_SIZE // 2))

                text = self.font.render(agent.name, True, (255, 255, 255))
                text_rect = text.get_rect(center=(px, py))
                self.screen.blit(text, text_rect)

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
    def get_sprite(sheet: pygame.Surface, frame, width, height, _rows, cols) -> pygame.Surface:
        # TODO: this one may be useful to process player sprites
        """Extracts a single sprite from a sprite sheet.

        Args:
            sheet: The loaded sprite sheet Surface.
            frame: The index of the sprite to extract (starting from 0, going row by row).
            width: The width of each sprite.
            height: The height of each sprite.
            _rows: The number of rows in the sprite sheet.
            cols: The number of columns in the sprite sheet.

        Returns:
            A pygame.Surface containing the extracted sprite.
        """
        row = frame // cols
        col = frame % cols
        x = col * width
        y = row * height
        sprite = pygame.Surface((width, height), pygame.SRCALPHA)  # Create a transparent surface
        sprite.blit(sheet, (0, 0), (x, y, width, height))
        return sprite


class Button:
    BACKGROUND = (20, 21, 22)
    HOVER_BACKGROUND = (40, 150, 90)
    CLICK_BACKGROUND = (180, 80, 40)

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
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            return True
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
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
