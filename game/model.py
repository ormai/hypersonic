from random import choice
from collections import deque

from game.explosion import Explosion
from game.entities import Agent, Bomb, CellType
from game.layouts import LAYOUTS
from game.log import get_logger

log = get_logger(__name__)


class Game:
    """Game logic"""

    MAX_TURNS = 200
    HEIGHT = 11
    WIDTH = 13
    START_POSITIONS = [
        (0, 0),
        (WIDTH - 1, HEIGHT - 1),
        (WIDTH - 1, 0),
        (0, HEIGHT - 1),
    ]
    BOMB_LIFETIME = 8
    DIRECTIONS = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def __init__(self, agents: list[Agent]):
        """
        Parameters:
            agents (list[str]): a list of commands to execute the agent subprocesses
        """

        assert len(agents) == 2, "For now, the game is played with 2 players only."

        self.running = True
        self.__turn = 0
        self.__bombs: list[Bomb] = []
        self.__agents = agents
        self.explosions: set[tuple[int, int]] = set()  # Set of (x, y) tuples for current explosions
        self.explosion_visuals: list[Explosion] = []
        self.__grid = [list(row) for row in choice(LAYOUTS)]

        for agent in self.__agents:
            agent.send_prelude(Game.WIDTH, Game.HEIGHT)

        assert all(len(row) == Game.WIDTH for row in self.__grid) and len(
            self.__grid) == Game.HEIGHT, f"Grid must be {Game.WIDTH}x{Game.HEIGHT}"

    def __tick_bombs(self) -> list[Bomb]:
        """Ticks all active bombs and returns the ones that explode in this turn"""
        exploding: list[Bomb] = []
        remaining: list[Bomb] = []
        for bomb in self.__bombs:
            if bomb.tick():
                exploding.append(bomb)
                self.__agents[bomb.owner_id].bombs_left += 1  # give back to agent
            else:
                remaining.append(bomb)
        self.__bombs = remaining
        return exploding

    def __propagate_explosions(self, exploding_bombs: list[Bomb]):
        self.explosions.clear()  # previous explosions
        newly_exploded_coordinates: set[tuple[int, int]] = set()
        processed_bomb_coordinates: set[tuple[int, int]] = set((b.x, b.y) for b in exploding_bombs)

        # In this league, players are not hurt by bombs (they are using practice explosives).

        queue = deque(exploding_bombs)
        while queue:
            bomb = queue.popleft()
            newly_exploded_coordinates.add((bomb.x, bomb.y))  # center of explosion
            for dx, dy in Game.DIRECTIONS:  # 4 directions
                for i in range(1, bomb.range):
                    nx, ny = bomb.x + dx * i, bomb.y + dy * i
                    if not self.in_bounds(nx, ny):
                        break
                    newly_exploded_coordinates.add((nx, ny))

                    # destroy boxes hit by explosion
                    if self.__grid[ny][nx] == CellType.BOX.value:
                        self.__grid[ny][nx] = CellType.FLOOR.value
                        self.__agents[bomb.owner_id].boxes_destroyed += 1
                        break  # explosion stops after hitting a box

                    # explosion triggers bombs nearby
                    for other_bomb in self.__bombs:
                        if not other_bomb.exploded and other_bomb.x == nx and other_bomb.y == ny:
                            if (other_bomb.x, other_bomb.y) not in processed_bomb_coordinates:
                                other_bomb.timer = 0  # detonate immediately
                                other_bomb.exploded = True  # Mark for removal later
                                # bomb exploded so return it to the agent
                                self.__agents[bomb.owner_id].bombs_left += 1
                                if other_bomb not in queue:
                                    queue.append(other_bomb)
                                processed_bomb_coordinates.add((other_bomb.x, other_bomb.y))

        # Update the main explosion set for collision detection this turn
        self.explosions = newly_exploded_coordinates

        # Remove chain-reacted bombs from main list
        self.__bombs = [bomb for bomb in self.__bombs if not bomb.exploded]

    def __parse_action(self, agent_id: int, action: str) -> tuple[str, int, int]:
        pack = action.split(maxsplit=3)
        if len(pack) > 3:
            cmd, x, y, msg = pack
            self.__agents[agent_id].message = msg
        elif len(pack) == 3:
            cmd, x, y = pack
            self.__agents[agent_id].message = ""
        else:
            raise ValueError(f"Invalid command, expected was 'BOMB x y' or 'MOVE x y', found '{action}'")
        return cmd.upper(), int(x), int(y)

    def __path(self, src: tuple[int, int], dst: tuple[int, int]) -> tuple[int, int] | None:
        """
        Find the short walkable path in the map

        Args:
            src: A tuple (row, col) representing the beginning of the path
            dst: A tuple (row, col) representing the end of the path

        Returns:
            The next cell (row, col) after src in the path to dst or None if
            there is no path or no next cell
        """
        queue = deque([(src, [src])])  # (current_cell, path_so_far)
        visited = {src}

        while queue:
            current_cell, path = queue.popleft()
            if current_cell == dst:
                return path[1] if len(path) > 1 else None

            for dr, dc in Game.DIRECTIONS:
                row, col = current_cell[0] + dr, current_cell[1] + dc
                if self.walkable(col, row) and (row, col) not in visited:
                    visited.add((row, col))
                    new_path = list(path)
                    new_path.append((row, col))
                    queue.append(((row, col), new_path))
        return None

    def __process_agent_actions(self, actions: dict[int, str]):
        """
        Takes raw action strings parses them and acts upon them

        Return:
            list[bombs]: new bombs placed
        """
        for agent_id, action in actions.items():
            agent = self.__agents[agent_id]
            cmd, x, y = self.__parse_action(agent_id, action)
            if cmd == "BOMB":
                # bomb placement and movement happen in the same turn
                if agent.bombs_left > 0:
                    if not any(b.x == agent.x and b.y == agent.y
                               for b in self.__bombs):
                        self.__bombs.append(
                            Bomb(
                                agent.id,
                                agent.x,
                                agent.y,
                                Game.BOMB_LIFETIME,
                                agent.bomb_range,
                            )
                        )
                        agent.bombs_left -= 1
                        log.info(f"{agent.name} places a bomb at {agent.x} {agent.y}")
                    else:
                        log.warning(f"{agent.name} tried to place a bomb" +
                                    f"at {x} {y}, but there is one there already")
                else:
                    log.info(f"{agent.name} wants to place a bomb but cannot")
            elif cmd != "MOVE":
                log.error(f"({agent.name}) invalid input. Expected 'MOVE" +
                          f" x y | BOMB x y, but found '{cmd} {x} {y}'")

            agent.last_action = f"{cmd} {x} {y}"
            self.__move(agent, x, y)

    def __move(self, agent: Agent, x: int, y: int):
        if agent.x == x and agent.y == y:
            return  # otherwise it loops between two neighboring cells

        # Using the MOVE command followed by grid coordinates will make the
        # player attempt to move one cell closer to those coordinates. The
        # player will automatically compute the shortest path within the grid
        # to get to the target point. If the given coordinates are impossible
        # to get to, the player will instead target the valid cell closest to
        # the given coordinates.

        # find the closest valid cell
        while not self.walkable(x, y):
            log.debug(f"destination not walkable ({x}, {y})")
            if alternative := min(
                    [(x + dx, y + dy) for dx, dy in Game.DIRECTIONS if self.walkable(x + dx, y + dy)],
                    key=lambda cell: abs(agent.x - cell[0]) + abs(agent.y - cell[1]),
                    default=None):
                x, y = alternative
                log.debug(f"found alternative destination ({x}, {y})")
            else:
                break

        if next_cell := self.__path((agent.y, agent.x), (y, x)):
            agent.y, agent.x = next_cell
            log.info(f"{agent.name} moves to ({agent.x}, {agent.y})")
        else:
            log.warning(f"{agent.name} cannot reach ({x}, {y})")

    def update(self, actions: dict[int, str]):
        """
        Processes one game turn.
        Order: Tick bombs, Explode, Spawn Items, Resolve Player Actions, Update Visuals
        """

        log.info(f"# Turn {self.__turn + 1}")
        self.__propagate_explosions(self.__tick_bombs())

        # update explosion visuals
        self.explosion_visuals = [v for v in self.explosion_visuals if v.tick()]
        self.explosion_visuals += [Explosion(x, y) for x, y in self.explosions if
                                   not any(v.x == x and v.y == y for v in self.explosion_visuals)]

        self.__process_agent_actions(actions)
        self.__turn += 1
        log.info("")

    @staticmethod
    def in_bounds(x: int, y: int) -> bool:
        return 0 <= x < Game.WIDTH and 0 <= y < Game.HEIGHT

    def walkable(self, x: int, y: int) -> bool:
        """Check if an agent can move at the cell (x, y)"""

        if not Game.in_bounds(x, y):
            return False

        # [...] If a bomb is already occupying that cell, the player won't be
        # able to move there.

        # Players can occupy the same cell as a bomb only when the bomb
        # appears on the same turn as when the player enters the cell.

        bomb = next((b for b in self.__bombs if b.x == x and b.y == y), None)
        if bomb is not None and bomb.timer < Game.BOMB_LIFETIME:
            return False

        return self.__grid[y][x] == CellType.FLOOR.value

    @property
    def grid(self) -> list[list[str]]:
        return self.__grid

    @property
    def turn(self) -> int:
        return self.__turn

    @property
    def agents(self) -> list[Agent]:
        return self.__agents

    @property
    def bombs(self) -> list[Bomb]:
        return self.__bombs