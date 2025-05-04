from random import choice
from collections import deque, defaultdict

from .entities import Agent, Bomb, CellType
from .layouts import LAYOUTS
from .log import get_logger

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

    # Clockwise directions
    DIRECTIONS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    DIRECTIONS_MAPPING = dict(zip(DIRECTIONS, ("up", "right", "down", "left")))

    def __init__(self, agents: list[Agent]):
        """
        Parameters:
            agents (list[str]): a list of Agents that play the game
        """

        assert len(agents) == 2, "For now, the game is played with 2 players only."

        self.running = True  # whether the simulation ended
        self.paused = True  # whether the simulation was temporarily paused
        self.turn = 0
        self.bombs: list[Bomb] = []
        self.agents = agents
        self.explosions: set[tuple[int, int]] = set()
        self.grid = [list(row) for row in choice(LAYOUTS)]
        self.boxes_left = self.count_boxes_left()

        for agent in self.agents:
            agent.send_prelude(Game.WIDTH, Game.HEIGHT)

        assert all(len(row) == Game.WIDTH for row in self.grid) and len(
            self.grid) == Game.HEIGHT, f"Grid must be {Game.WIDTH}x{Game.HEIGHT}"

    def count_boxes_left(self) -> int:
        return sum(row.count(CellType.BOX.value) for row in self.grid)

    def tick_bombs(self) -> list[Bomb]:
        """Ticks all active bombs and returns the ones that explode in this turn"""
        exploding: list[Bomb] = []
        remaining: list[Bomb] = []
        for bomb in self.bombs:
            if bomb.tick():
                exploding.append(bomb)
                self.agents[bomb.owner_id].bombs_left += 1  # give back to agent
            else:
                remaining.append(bomb)
        self.bombs = remaining
        return exploding

    def propagate_explosions(self, exploding_bombs: list[Bomb]):
        newly_exploded_coordinates: set[tuple[int, int]] = set()
        processed_bomb_coordinates: set[tuple[int, int]] = set((b.x, b.y) for b in exploding_bombs)
        box_hit_by: dict[tuple[int, int], set[int]] = defaultdict(set)  # box coordinates -> set of owner_id

        # In this league, players are not hurt by bombs (they are using practice explosives).

        queue = deque(exploding_bombs)
        while queue:
            bomb = queue.popleft()
            newly_exploded_coordinates.add((bomb.x, bomb.y))  # center of explosion
            for dx, dy in Game.DIRECTIONS:
                for i in range(1, bomb.range):
                    nx, ny = bomb.x + dx * i, bomb.y + dy * i
                    if not self.in_bounds(nx, ny):
                        break
                    newly_exploded_coordinates.add((nx, ny))

                    # destroy boxes hit by explosion
                    if self.grid[ny][nx] == CellType.BOX.value:
                        box_hit_by[(nx, ny)].add(bomb.owner_id)
                        break  # explosion stops after hitting a box

                    bomb_found = False

                    # explosion triggers bombs nearby
                    for other_bomb in self.bombs:
                        if other_bomb.x == nx and other_bomb.y == ny:
                            bomb_found = True
                            if other_bomb.timer > 0:
                                if (other_bomb.x, other_bomb.y) not in processed_bomb_coordinates:
                                    log.debug(f"{bomb} exploded and detonated immediately {other_bomb}")
                                    other_bomb.timer = 0  # detonate immediately
                                    # bomb exploded so return it to the agent
                                    self.agents[other_bomb.owner_id].bombs_left += 1
                                    if other_bomb not in queue:
                                        queue.append(other_bomb)
                                    processed_bomb_coordinates.add((other_bomb.x, other_bomb.y))

                    if bomb_found:
                        break

        # Update the main explosion set for collision detection this turn
        self.explosions = newly_exploded_coordinates

        # destroy boxes and assign points to owners
        for (x, y), owners in box_hit_by.items():
            if self.grid[y][x] == CellType.BOX.value:
                self.grid[y][x] = CellType.FLOOR.value
                for owner_id in owners:
                    self.agents[owner_id].boxes_blown_up += 1

        # Remove chain-reacted bombs from main list
        self.bombs = [bomb for bomb in self.bombs if bomb.timer > 0]

    def parse_action(self, agent_id: int, action: str) -> tuple[str, int, int]:
        pack = action.split(maxsplit=3)
        if len(pack) > 3:
            cmd, x, y, msg = pack
            self.agents[agent_id].message = msg
        elif len(pack) == 3:
            cmd, x, y = pack
            self.agents[agent_id].message = ""
        else:
            raise ValueError(f"Invalid command, expected was 'BOMB x y' or 'MOVE x y', found '{action}'")
        return cmd.upper(), int(x), int(y)

    def path(self, src: tuple[int, int], dst: tuple[int, int]) -> tuple[int, int] | None:
        """
        Find the short walkable path in the map

        Args:
            src: A tuple (row, col) representing the beginning of the path
            dst: A tuple (row, col) representing the end of the path

        Returns:
            The next cell (row, col) after hypersonic in the path to dst or None if
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

    def process_agent_actions(self, actions: dict[int, str]):
        """
        Takes raw action strings parses them and acts upon them

        Return:
            list[bombs]: new bombs placed
        """
        for agent_id, action in actions.items():
            agent = self.agents[agent_id]
            try:
                cmd, x, y = self.parse_action(agent_id, action)
                if not Game.in_bounds(x, y):
                    raise ValueError(f"{agent.name}, out of bounds coordinates ({x}, {y})")
                if cmd == "BOMB":
                    # bomb placement and movement happen in the same turn
                    if agent.bombs_left > 0:
                        if not any(b.x == agent.x and b.y == agent.y for b in self.bombs):
                            self.bombs.append(Bomb(agent.id, agent.x, agent.y))
                            agent.bombs_left -= 1
                            log.info(f"{agent.name} places a bomb at ({agent.x}, {agent.y})")
                        else:
                            log.warning(f"{agent.name} tried to place a bomb " +
                                        f"at ({x}, {y}), but there is one there already")
                    else:
                        log.info(f"{agent.name} wants to place a bomb but cannot")
                elif cmd != "MOVE":
                    raise ValueError("Invalid command")
                self.move(agent, x, y)
            except ValueError as e:
                if action:
                    log.error(e)
                    log.warning(f"{agent.name} is disqualified for providing invalid input")
                agent.disqualified = True

    def move(self, agent: Agent, x: int, y: int):
        if agent.x == x and agent.y == y:
            agent.state = Agent.State.IDLE
            return  # otherwise it loops between two neighboring cells

        # > Using the MOVE command followed by grid coordinates will make the
        # > player attempt to move one cell closer to those coordinates. The
        # > player will automatically compute the shortest path within the grid
        # > to get to the target point. If the given coordinates are impossible
        # > to get to, the player will instead target the valid cell closest to
        # > the given coordinates.

        if not self.walkable(x, y):
            log.debug(f"destination not walkable ({x}, {y})")
            # We only look for the four adjacent cells to the destination --and
            # thus equally close to the destination (x, y), thus satisfying the
            # spec-- and pick the one that is walkable and closest to the
            # player. Knowing the map layouts and the behavior of all entities
            # we know that this will be enough. An example of a critical
            # situation might be that of a destination cell containing a box.
            # Now, if the candidate alternative cell contains a bomb --not
            # placed in the current turn-- we just fall back again on one of
            # the other three cells, one of which must be valid because:
            # (1) boxes are never placed in corners;
            # (2) there can be a maximum of two bombs placed simultaneously.

            # NOTE: when multiple alternatives are equally distant from
            #       the agent the directions are attempted in the order of the
            #       Game.DIRECTIONS list elements.
            x, y = min([(x + dx, y + dy) for dx, dy in Game.DIRECTIONS if self.walkable(x + dx, y + dy)],
                       key=lambda cell: abs(agent.x - cell[0]) + abs(agent.y - cell[1]))
            log.debug(f"alternative destination is ({x}, {y})")

        if next_cell := self.path((agent.y, agent.x), (y, x)):
            ny, nx = next_cell
            agent.direction = Game.DIRECTIONS_MAPPING[(nx - agent.x, ny - agent.y)]
            agent.previous_x, agent.previous_y = agent.x, agent.y
            agent.state = Agent.State.MOVE
            agent.x, agent.y = nx, ny
            log.info(f"{agent.name} moves to ({agent.x}, {agent.y})")
        else:
            agent.state = Agent.State.IDLE
            log.warning(f"{agent.name} cannot reach ({x}, {y})")

    def update(self):
        """
        Processes one game turn.
        """
        log.info(f"# Turn {self.turn + 1}")
        for agent in self.agents:
            agent.send_turn_state(self.agents, self.bombs, self.grid)

        self.propagate_explosions(self.tick_bombs())  # update previous state
        self.process_agent_actions({agent.id: agent.receive(self.turn) for agent in self.agents})  # add new state
        self.boxes_left = self.count_boxes_left()
        self.turn += 1

        # end game condition
        if self.turn >= Game.MAX_TURNS or self.boxes_left == 0 or any(a.disqualified for a in self.agents):
            self.running = False

    def get_winners(self) -> list[Agent]:
        """
        Returns:
            list[Agent]: all players that are qualified to be the winner

        It may return one agent, the only winner. If it returns two agents the
        game ended in a draw. Finally, if an empty list is returned, although
        a rare case, both players met a loose condition, thus nobody wins.
        """
        candidates = [a for a in self.agents if not a.disqualified]
        winning_score = max((agent.boxes_blown_up for agent in candidates), default=0)
        return [a for a in candidates if a.boxes_blown_up == winning_score]

    @staticmethod
    def in_bounds(x: int, y: int) -> bool:
        return 0 <= x < Game.WIDTH and 0 <= y < Game.HEIGHT

    def walkable(self, x: int, y: int) -> bool:
        """Check if an agent can move to the cell (x, y)"""

        if not Game.in_bounds(x, y):
            return False

        # [...] If a bomb is already occupying that cell, the player won't be
        # able to move there.

        # Players can occupy the same cell as a bomb only when the bomb
        # appears on the same turn as when the player enters the cell.

        bomb = next((b for b in self.bombs if b.x == x and b.y == y), None)
        if bomb is not None and bomb.timer < Bomb.LIFETIME:
            return False

        return self.grid[y][x] == CellType.FLOOR.value
