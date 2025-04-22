import pygame
from game.model import Game
from game.enums import CellType


class Display:
    CELL_SIZE = 100
    FLOOR_COLOR = (150, 150, 150)
    GRID_LINE_COLOR = (50, 50, 50)
    WALL_COLOR = (80, 80, 80)
    BOX_COLOR = (139, 69, 19)  # Saddle Brown
    BOMB_COLOR = (30, 30, 30)
    EXPLOSION_COLOR = (255, 165, 0)  # Orange
    AGENT_COLORS = [
        (0, 0, 255),  # Blue
        (255, 0, 0),  # Red
        (0, 255, 0),  # Green
        (255, 255, 0),  # Yellow
    ]

    def __init__(self, game: Game):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Hypersonic")

        self.game = game
        self.width = Game.WIDTH * Display.CELL_SIZE
        self.height = Game.HEIGHT * Display.CELL_SIZE
        try:
            self.font = pygame.font.Font("game/resources/JetBrainsMono-Regular.ttf", 20)
            self.big_font = pygame.font.Font("game/resources/JetBrainsMono-Regular.ttf", 50)
        except FileNotFoundError:
            self.font = pygame.font.Font(None, 20)
            self.big_font = pygame.font.Font(None, 50)
        self.text_height = self.font.size("A")[1]
        self.screen = pygame.display.set_mode((self.width, self.height + self.text_height))

    def draw(self) -> None:
        """Draw grid and all entities"""
        self.screen.fill(Display.FLOOR_COLOR)

        self.__draw_grid()
        self.__draw_explosions()
        self.__draw_bombs()
        self.__draw_agents()

        scores = ", ".join(f"{agent.name}: {agent.bombs_destroyed}" for agent in self.game.agents)
        text = (f"Turn: {self.game.turn + 1:-03}/{Game.MAX_TURNS}, "
                f"Alive: {len(self.game.alive_agents())}, {scores}")
        pygame.draw.rect(self.screen, (0, 0, 0), pygame.rect.Rect(0, self.height, self.width, self.text_height))
        self.screen.blit(self.font.render(text, True, (255, 255, 255), (0, 0, 0)), (5, self.height))

        pygame.display.flip()

    def __draw_grid(self) -> None:
        for r in range(Game.HEIGHT):
            for c in range(Game.WIDTH):
                rect = pygame.Rect(c * Display.CELL_SIZE, r * Display.CELL_SIZE, Display.CELL_SIZE, Display.CELL_SIZE)
                if self.game.grid[r][c] == CellType.BOX.value:
                    pygame.draw.rect(self.screen, Display.BOX_COLOR, rect)
                pygame.draw.rect(self.screen, Display.GRID_LINE_COLOR, rect, 1)

    def __draw_agents(self) -> None:
        for agent in self.game.agents:
            if agent.is_alive:
                # TODO: display agent message
                px = agent.x * Display.CELL_SIZE + Display.CELL_SIZE // 2
                py = agent.y * Display.CELL_SIZE + Display.CELL_SIZE // 2
                pygame.draw.circle(self.screen, Display.AGENT_COLORS[agent.id % len(Display.AGENT_COLORS)], (px, py),
                                   Display.CELL_SIZE // 3)
                text = self.font.render(str(agent.id), True, (255, 255, 255))
                text_rect = text.get_rect(center=(px, py))
                self.screen.blit(text, text_rect)

    def __draw_bombs(self) -> None:
        for bomb in self.game.bombs:
            if not bomb.exploded:
                px = bomb.x * self.CELL_SIZE
                py = bomb.y * self.CELL_SIZE
                rect = pygame.Rect(
                    px + Display.CELL_SIZE // 4,
                    py + Display.CELL_SIZE // 4,
                    Display.CELL_SIZE // 2,
                    Display.CELL_SIZE // 2
                )
                pygame.draw.rect(self.screen, Display.BOMB_COLOR, rect)
                text = self.font.render(str(bomb.timer), True, (255, 255, 255))
                text_rect = text.get_rect(center=rect.center)
                self.screen.blit(text, text_rect)

    def __draw_explosions(self) -> None:
        for explosion in self.game.explosion_visuals:
            px = explosion.x * self.CELL_SIZE
            py = explosion.y * self.CELL_SIZE
            # rect = pygame.Rect(px, py, cell_size, cell_size)
            # Fade effect based on timer
            alpha = max(0, min(255, int(255 * (explosion.timer / explosion.TICK_DURATION))))
            surface = pygame.Surface((Display.CELL_SIZE, Display.CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(surface, (*self.EXPLOSION_COLOR, alpha), surface.get_rect())
            self.screen.blit(surface, (px, py))

    def show_final_message(self, message: str) -> None:
        win_surface = self.big_font.render(message, True, (255, 215, 0))
        win_rect = win_surface.get_rect(center=(self.width // 2, self.height // 2))
        bg_rect = win_rect.inflate(20, 20)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), bg_rect)  # Semi-transparent black bg
        self.screen.blit(win_surface, win_rect)
        pygame.display.flip()
