from collections import deque
from game.explosion import Explosion
from game.bomb import Bomb
from game.agent import Agent
from game.enums import CellType


def get_initial_input_string(agent_id: int) -> str:
    """Generates the initial input string for the agent."""
    return f"{Game.WIDTH} {Game.HEIGHT} {agent_id}"


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
    TIMEOUT_FIRST_TURN = 1.0  # Seconds
    TIMEOUT_PER_TURN = 0.1  # Seconds
    BOMB_LIFETIME = 8

    def __init__(self, agent_commands: list[list[str]]):
        """
        Initializes a new GameState

        Parameters:
            agent_commands (list[str]): a list of commands to execute the agent subprocesses
        """

        assert 2 <= len(agent_commands) <= 4, "There can be 2, 3 or 4 agents"

        self.running = True
        self.turn = 0
        self.agents: list[Agent] = []
        self.bombs: list[Bomb] = []
        self.explosions: set[int] = set()  # Set of (x, y) tuples for current explosions
        self.explosion_visuals: list[Explosion] = []  # List of Explosion objects for drawing

        self.grid = [
            list("...0.0.0.0..."),
            list(".0.........0."),
            list("............."),
            list(".0..0.0.0..0."),
            list("............."),
            list("0..0.0.0.0..0"),
            list("............."),
            list(".0..0.0.0..0."),
            list("............."),
            list(".0.........0."),
            list("...0.0.0.0..."),
        ]

        for i, cmd in enumerate(agent_commands):
            start_x, start_y = self.START_POSITIONS[i]
            self.agents.append(Agent(i, start_x, start_y, cmd))

    def get_cell(self, x: int, y: int) -> str | None:
        """Bound checked cell accessor"""
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            return self.grid[y][x]
        return None

    def can_move(self, x: int, y: int) -> bool:
        """Check if an agent can move at the cell (x, y)"""
        cell = self.get_cell(x, y)
        return cell is not None and cell != CellType.BOX

    def get_turn_state_string(self) -> str:
        """
        Generates the input string for all agents, representing the game
        state at the beginning of the turn.
        """
        grid = "\n".join("".join(row) for row in self.grid)
        entities: list[str] = list(map(lambda a: a.get_entity_str(), self.alive_agents())) + list(
            map(lambda b: b.get_entity_str(), self.unexploded_bombs()))
        return f"{grid}\n{len(entities)}\n{'\n'.join(entities)}"

    def __update_bombs(self) -> list[Bomb]:
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

    def __explode_bombs(self, exploding_bombs: list[Bomb]):
        self.explosions.clear()  # previous explosions
        newly_exploded_coordinates = set()
        queue = deque(exploding_bombs)
        processed_bomb_coordinates = set((b.x, b.y) for b in exploding_bombs)

        while queue:
            bomb = queue.popleft()
            newly_exploded_coordinates.add((bomb.x, bomb.y))  # Bomb location itself explodes

            # Propagate in 4 directions
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                for i in range(1, bomb.range):
                    nx, ny = bomb.x + dx * i, bomb.y + dy * i

                    # Check bounds
                    if not (0 <= nx < self.WIDTH and 0 <= ny < self.HEIGHT):
                        break

                    newly_exploded_coordinates.add((nx, ny))

                    # Explosion destroys boxes
                    cell = self.get_cell(nx, ny)
                    if cell == CellType.BOX:
                        self.grid[ny][nx] = CellType.EMPTY  # Destroy the box
                        break  # Explosion stops after hitting a box

                    # Chain reaction: Check for other bombs
                    for other_bomb in self.bombs:
                        if not other_bomb.exploded and other_bomb.x == nx and other_bomb.y == ny:
                            if (other_bomb.x, other_bomb.y) not in processed_bomb_coordinates:
                                # Trigger this bomb immediately
                                # Will explode next logical step if not already
                                other_bomb.timer = 0
                                if other_bomb not in queue:
                                    queue.append(other_bomb)
                                processed_bomb_coordinates.add((other_bomb.x, other_bomb.y))
                                # Return bomb capacity immediately on chain reaction
                                self.agents[bomb.owner_id].bombs_left += 1

                                # Mark this bomb as handled for explosion logic
                                other_bomb.exploded = True  # Mark for removal later

                    # Explosion continues through floor and items
                    # Assuming items don't block explosions
                    if cell == CellType.EMPTY:
                        continue

        # Update the main explosion set for collision detection this turn
        self.explosions = newly_exploded_coordinates

        # Remove chain-reacted bombs from main list
        self.bombs = [b for b in self.bombs if not b.exploded]

    def update(self, actions):
        """
        Processes one game turn.
        Order: Tick bombs, Explode, Spawn Items, Resolve Player Actions, Update Visuals
        """
        # 1. Tick Bombs & Identify Explosions
        exploding_bombs = self.__update_bombs()

        # 2. Calculate Explosion Propagation
        self.__explode_bombs(exploding_bombs)

        # 3. Update Explosion Visuals (separate from logic set)
        next_explosion_visuals = []
        for vis in self.explosion_visuals:
            if vis.tick():  # If timer > 0 after ticking
                next_explosion_visuals.append(vis)

        for x, y in self.explosions:
            # Avoid adding duplicate visuals if explosion persists
            if not any(ev.x == x and ev.y == y for ev in next_explosion_visuals):
                next_explosion_visuals.append(Explosion(x, y))
        self.explosion_visuals = next_explosion_visuals

        # 4. Process Player Actions (Move, Bomb)
        player_targets = {}  # player_id -> (new_x, new_y)
        bombs_to_place = []  # List of Bomb objects to add next turn

        for agent_id, action_str in enumerate(actions):
            agent = self.agents[agent_id]
            if not agent.is_alive:
                continue

            parts = action_str.split()
            command = parts[0].upper()

            target_x, target_y = agent.x, agent.y
            if command == "MOVE" and len(parts) >= 3:
                try:
                    req_x, req_y = int(parts[1]), int(parts[2])
                    # adjacent or same cell
                    if abs(req_x - agent.x) + abs(req_y - agent.y) <= 1:
                        if self.can_move(req_x, req_y):
                            target_x, target_y = req_x, req_y
                except (ValueError, IndexError):
                    pass  # Invalid command format, stay put
                agent.last_action = f"MOVE {target_x} {target_y}"
            elif command == "BOMB" and len(parts) >= 3:
                if agent.bombs_left > 0:
                    is_bomb_present = any(
                        b.x == agent.x and b.y == agent.y
                        for b in self.bombs + bombs_to_place
                    )
                    if not is_bomb_present:
                        bombs_to_place.append(
                            Bomb(
                                agent.id,
                                agent.x,
                                agent.y,
                                self.BOMB_LIFETIME,
                                agent.bomb_range,
                            )
                        )
                        agent.bombs_left -= 1
                        agent.last_action = f"BOMB {agent.x} {agent.y}"
                    else:
                        raise ValueError(f"Agent {agent.id} tried {action_str} but there is one there already")
                else:
                    print(f"{agent.id} wants to place a bomb but cannot")
                target_x, target_y = agent.x, agent.y
            else:
                raise ValueError(f"Agent {agent.id} issued an invalid command {action_str}")
            player_targets[agent_id] = (target_x, target_y)

        # 5. Resolve Movements & Collisions (Simplistic: players occupy target if possible)
        # More complex logic needed for head-on collisions, etc.
        # This version just lets players move if target is not blocked.
        for agent_id, (new_x, new_y) in player_targets.items():
            agent = self.agents[agent_id]
            if agent.is_alive:
                # Check again if target is blocked (could have changed if box exploded?)
                if self.can_move(new_x, new_y):
                    agent.x, agent.y = new_x, new_y
                else:
                    raise ValueError(f"Agent {agent.id} tried to move to an invalid position")

        # TODO: do agents get damaged by explosions?
        # 7. Check Players caught in explosions (after movement)
        for player in self.agents:
            if player.is_alive:
                if (player.x, player.y) in self.explosions:
                    player.is_alive = False
                    print(
                        f"Player {player.id} eliminated by explosion at ({player.x},{player.y})!"
                    )
                    # Return bombs if player is eliminated? Depends on rules. Assume yes.
                    # No, bombs explode where they are. Bomb count is separate.

        # 8. Add newly placed bombs to the list
        self.bombs.extend(bombs_to_place)

    def alive_agents(self) -> list[Agent]:
        return list(filter(lambda agent: agent.is_alive, self.agents))

    def unexploded_bombs(self) -> list[Bomb]:
        return list(filter(lambda bomb: not bomb.exploded, self.bombs))

    def is_game_over(self):
        alive_players = [p for p in self.agents if p.is_alive]
        return len(alive_players) <= 1

    def get_winner(self):
        alive_players = [p for p in self.agents if p.is_alive]
        if len(alive_players) == 1:
            return alive_players[0]
        elif len(alive_players) == 0:
            # Could be a draw if multiple players die in the same explosion
            return None  # Or handle draws specifically
        return None  # Game not over
