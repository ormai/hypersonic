from game.explosion import Explosion
from game.bomb import Bomb
from game.agent import Agent
from game.enums import CellType
from game.layouts import LAYOUTS
from random import choice
from collections import deque


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

    def __init__(self, agent_commands: list[list[str]]):
        """
        Parameters:
            agent_commands (list[str]): a list of commands to execute the agent subprocesses
        """

        if not 2 <= len(agent_commands) <= 4:
            raise ValueError("There can be 2, 3 or 4 agents")

        self.running = True
        self.turn = 0
        self.agents: list[Agent] = []
        self.bombs: list[Bomb] = []
        self.explosions: set[tuple[int, int]] = set()  # Set of (x, y) tuples for current explosions
        self.explosion_visuals: list[Explosion] = []
        self.grid = [list(row) for row in choice(LAYOUTS)]

        assert all(len(row) == self.WIDTH for row in self.grid) and len(
            self.grid) == self.HEIGHT, f"Grid must be {self.WIDTH}x{self.HEIGHT}"

        for i, cmd in enumerate(agent_commands):
            start_x, start_y = self.START_POSITIONS[i]
            self.agents.append(Agent(i, start_x, start_y, cmd))

    def check_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT

    def can_move(self, x: int, y: int) -> bool:
        """Check if an agent can move at the cell (x, y)"""
        return self.check_bounds(x, y) and self.grid[y][x] != CellType.BOX.value

    def get_serialized_turn_state(self) -> str:
        """
        Generates the input string for all agents, representing the game
        state at the beginning of the turn.
        """
        entities = [e.serialize() for e in self.alive_agents() + self.unexploded_bombs()]
        return f"{'\n'.join(''.join(row) for row in self.grid)}\n{len(entities)}\n{'\n'.join(entities)}"

    @staticmethod
    def get_serialized_prelude(agent_id: int) -> str:
        """Generates the initial input string for the agent."""
        return f"{Game.WIDTH} {Game.HEIGHT} {agent_id}"

    def __tick_bombs(self) -> list[Bomb]:
        """Ticks all active bombs and returns the ones that explode in this turn"""
        exploding: list[Bomb] = []
        remaining: list[Bomb] = []
        for bomb in self.bombs:
            if bomb.tick():
                exploding.append(bomb)
                # Return bomb to owner if it explodes
                self.agents[bomb.owner_id].bombs_left += 1
            else:
                remaining.append(bomb)
        self.bombs = remaining
        return exploding

    def __propagate_explosions(self, exploding_bombs: list[Bomb]):
        self.explosions.clear()  # previous explosions
        newly_exploded_coordinates: set[tuple[int, int]] = set()
        queue = deque(exploding_bombs)
        processed_bomb_coordinates: set[tuple[int, int]] = set((b.x, b.y) for b in exploding_bombs)

        while queue:
            bomb = queue.popleft()
            newly_exploded_coordinates.add((bomb.x, bomb.y))  # Bomb location itself explodes

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:  # 4 directions
                for i in range(1, bomb.range):
                    nx, ny = bomb.x + dx * i, bomb.y + dy * i
                    if not self.check_bounds(nx, ny):
                        break
                    newly_exploded_coordinates.add((nx, ny))

                    # destroy boxes hit by explosion
                    if self.grid[ny][nx] == CellType.BOX.value:
                        self.grid[ny][nx] = CellType.EMPTY.value
                        break  # explosion stops after hitting a box

                    # explosion triggers bombs nearby
                    for other_bomb in self.bombs:
                        if not other_bomb.exploded and other_bomb.x == nx and other_bomb.y == ny:
                            if (other_bomb.x, other_bomb.y) not in processed_bomb_coordinates:
                                other_bomb.timer = 0  # detonate immediately
                                other_bomb.exploded = True  # Mark for removal later
                                # bomb exploded so return it to the agent
                                self.agents[bomb.owner_id].bombs_left += 1
                                if other_bomb not in queue:
                                    queue.append(other_bomb)
                                processed_bomb_coordinates.add((other_bomb.x, other_bomb.y))

        # Update the main explosion set for collision detection this turn
        self.explosions = newly_exploded_coordinates

        # Remove chain-reacted bombs from main list
        self.bombs = [bomb for bomb in self.bombs if not bomb.exploded]

    @staticmethod
    def __parse_action(action: str) -> tuple[str, int, int]:
        pack = action.split(maxsplit=3)
        if len(pack) > 3:
            cmd, x, y, msg = pack
            # TODO: show msg on the display
        elif len(pack) == 3:
            cmd, x, y = pack
        else:
            raise ValueError(f"Invalid command, expected was 'BOMB x y' or 'MOVE x y', found '{action}'")
        return cmd.upper(), int(x), int(y)

    def __process_agent_actions(self, actions: dict[int, str]) -> tuple[list[Bomb], dict[int, tuple[int, int]]]:
        """Returns new bombs placed and a map of the agent next movement targets"""
        agent_targets: dict[int, tuple[int, int]] = {}
        new_bombs: list[Bomb] = []
        for agent_id, action in actions.items():
            agent = self.agents[agent_id]
            if agent.is_alive:
                cmd, req_x, req_y = self.__parse_action(action)
                target_x, target_y = agent.x, agent.y  # default: no movement
                match cmd:
                    case "MOVE":
                        # adjacent or same cell
                        if abs(req_x - agent.x) + abs(req_y - agent.y) <= 1:
                            if self.can_move(req_x, req_y):
                                target_x, target_y = req_x, req_y
                        print(f"{agent.id} moves to {req_x}, {req_y}")
                    case "BOMB":
                        if agent.bombs_left > 0:
                            if not any(b.x == agent.x and b.y == agent.y for b in self.bombs + new_bombs):
                                new_bombs.append(
                                    Bomb(
                                        agent.id,
                                        agent.x,
                                        agent.y,
                                        self.BOMB_LIFETIME,
                                        agent.bomb_range,
                                    )
                                )
                                agent.bombs_left -= 1
                            else:
                                # TODO: maybe this not an error
                                raise ValueError(
                                    f"{agent.id} tried to place a bomb at {req_x} {req_y}, but there is one there already")
                            print(f"{agent.id} places a bomb")
                        else:
                            print(f"{agent.id} wants to place a bomb but cannot")
                        target_x, target_y = agent.x, agent.y
                    case _:
                        raise ValueError(f"({agent.id}) invalid input." +
                                         "Expected 'MOVE x y | BOMB x y'" +
                                         f"but found '{cmd} {req_x} {req_y}'")
                agent.last_action = f"{cmd} {agent.x} {agent.y}"
                agent_targets[agent_id] = (target_x, target_y)
        return new_bombs, agent_targets

    def update(self, actions: dict[int, str]):
        """
        Processes one game turn.
        Order: Tick bombs, Explode, Spawn Items, Resolve Player Actions, Update Visuals
        """

        # In this league, players are not hurt by bombs (they are using practice explosives).

        print(f"# Turn {self.turn + 1}")

        self.__propagate_explosions(self.__tick_bombs())

        # update explosion visuals
        self.explosion_visuals = [v for v in self.explosion_visuals if v.tick()]
        self.explosion_visuals += [Explosion(x, y) for x, y in self.explosions if
                                   not any(v.x == x and v.y == y for v in self.explosion_visuals)]

        new_bombs, agent_targets = self.__process_agent_actions(actions)

        # 5. Resolve Movements & Collisions (Simplistic: players occupy target if possible)
        # More complex logic needed for head-on collisions, etc.
        # This version just lets players move if target is not blocked.
        for agent_id, (new_x, new_y) in agent_targets.items():
            agent = self.agents[agent_id]
            if agent.is_alive:
                # Check again if target is blocked (could have changed if box exploded?)
                if self.can_move(new_x, new_y):
                    agent.x, agent.y = new_x, new_y
                else:
                    raise ValueError(f"Agent {agent.id} tried to move to an invalid position")

        self.bombs += new_bombs
        print()

    def alive_agents(self) -> list[Agent]:
        return list(filter(lambda agent: agent.is_alive, self.agents))

    def unexploded_bombs(self) -> list[Bomb]:
        return list(filter(lambda bomb: not bomb.exploded, self.bombs))
