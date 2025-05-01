import os
import sys
from queue import Queue, Empty
from subprocess import Popen, PIPE, TimeoutExpired
from select import select
from abc import ABC, abstractmethod
from typing import override
from threading import Timer, Thread, Lock, Condition
from enum import Enum

from embasp.base.option_descriptor import OptionDescriptor
from embasp.languages.asp.answer_sets import AnswerSets
from embasp.languages.asp.asp_input_program import ASPInputProgram
from embasp.languages.asp.asp_mapper import ASPMapper
from embasp.languages.predicate import Predicate
from embasp.platforms.desktop.desktop_handler import DesktopHandler
from embasp.specializations.dlv2.desktop.dlv2_desktop_service import DLV2DesktopService

from .log import get_logger

log = get_logger(__name__)


class CellType(Enum):
    FLOOR = "."
    BOX = "0"


class EntityType(Enum):
    PLAYER = "0"
    BOMB = "1"


class Bomb:
    LIFETIME = 8
    RANGE = 3

    def __init__(self, owner_id, x: int, y: int):
        self.type = EntityType.BOMB.value
        self.owner_id = owner_id
        self.x, self.y = x, y
        self.timer = Bomb.LIFETIME
        self.range = Bomb.RANGE

    def __repr__(self):
        return f"Bomb(owner={self.owner_id}, pos=({self.x},{self.y}), timer={self.timer})"

    def tick(self) -> bool:
        """
        Decreases the bomb timer by one

        Returns:
            (bool): whether the bomb should explode in this round
        """
        if self.timer > 0:
            self.timer -= 1
        return self.timer == 0


class Agent(ABC):
    """An autonomous player"""

    INITIAL_TIMEOUT_S = 1.0  # Response time for the first turn ≤ 1000 ms
    TURN_TIMEOUT_S = 0.1  # Response time per turn ≤ 100 ms

    def __init__(self, agent_id: int, start_cell: tuple[int, int], name: str = ""):
        self.type = EntityType.PLAYER.value
        self.id = agent_id
        self.x, self.y = start_cell
        self.bombs_left = 1

        self.bomb_range = 3  # useless in this league
        self.message = ""
        self.name = name if name else f"Agent {agent_id}"

        # Victory Conditions
        # - You are the one who blew up the most boxes.
        self.boxes_blown_up = 0

        # Lose Conditions
        # - Your program does not respond in time.
        # - You provide invalid input.
        self.disqualified = False

        # These are used by the Display to animate the player
        self.state = Agent.State.IDLE
        self.direction = "down" if self.x == 0 else "up"
        self.previous_x, self.previous_y = start_cell

    def __repr__(self):
        return (f"Agent(id={self.id}, name={self.name}, pos=({self.x},{self.y})"
                + f", disqualified={self.disqualified}, "
                + f"bombs_left={self.bombs_left}, "
                + f"boxes_blown_up={self.boxes_blown_up})")

    @abstractmethod
    def send_turn_state(self, agents: list["Agent"], bombs: list[Bomb], grid: list[list[str]]):
        ...

    @abstractmethod
    def receive(self, turn: int) -> str:
        ...

    @abstractmethod
    def send_prelude(self, width: int, height: int):
        ...

    @abstractmethod
    def _serialize_turn_state(self,
                              agents: list["Agent"],
                              bombs: list[Bomb],
                              grid: list[list[str]]) -> str | list[Predicate]:
        ...

    def terminate(self):
        ...

    class State(Enum):
        IDLE = "idle"
        MOVE = "move"


def _reader_thread(pipe, queue):
    for line in iter(pipe.readline, ''):
        queue.put(line)
    pipe.close()


class ExecutableAgent(Agent):
    """
    An executable agent is a subprocess executing on its own. It gets the game state from
    the runner via stdin and outputs an action via stdout. For instance, it can be
    a python script or a compiled C++ program, i.e. an executable.
    """

    def __init__(self, agent_id: int, start_cell: tuple[int, int], cmd: list[str], name: str = ""):
        """
        Args:
            cmd (list[str]): the command for the subprocess, split
            agent_id (int): an identifier for the agent, imposes an order of processing in the game
            start_cell (tuple[int, int]): start position in the grid, should be one of the corners
            name (str): an optional display name
        """
        super().__init__(agent_id, start_cell, name)
        self.process: Popen | None = Popen(
            cmd,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            bufsize=0,
            universal_newlines=True,
        )

        if sys.platform == 'win32':
            self.output_queue = Queue()
            self.error_queue = Queue()
            self.stdout_thread = Thread(target=_reader_thread, args=(self.process.stdout, self.output_queue),
                                        daemon=True)
            self.stderr_thread = Thread(target=_reader_thread, args=(self.process.stderr, self.error_queue),
                                        daemon=True)
            self.stdout_thread.start()
            self.stderr_thread.start()

        log.debug(f"Started {self.name} (PID: {self.process.pid}): {' '.join(cmd)}")

    def __terminated(self) -> bool:
        """Check if the underlying subprocess has terminated"""
        return self.process is None or self.process.poll() is not None

    @override
    def _serialize_turn_state(self, agents: list[Agent], bombs: list[Bomb], grid: list[list[str]]) -> str:
        entities = [f"{a.type} {a.id} {a.x} {a.y} {a.bombs_left} {a.bomb_range}" for a in agents]
        entities += [f"{b.type} {b.owner_id} {b.x} {b.y} {b.timer} {b.range}" for b in bombs]
        return f"{'\n'.join(''.join(row) for row in grid)}\n{len(entities)}\n{'\n'.join(entities)}"

    @override
    def send_turn_state(self, agents: list[Agent], bombs: list[Bomb], grid: list[list[str]]):
        self.__send(self._serialize_turn_state(agents, bombs, grid))

    def __send(self, data: str):
        """Send turn state information to the subprocess"""
        if self.__terminated() or self.process.stdin is None:
            raise ConnectionError(f"Cannot send data to agent {self.id}")

        try:
            self.process.stdin.write(data + "\n")
            self.process.stdin.flush()
        except (IOError, BrokenPipeError, OSError) as e:
            raise ConnectionError(f"Error sending data to agent {self.id}: {e}")

    @override
    def send_prelude(self, width: int, height: int):
        self.__send(f"{width} {height} {self.id}")

    @override
    def receive(self, turn: int) -> str:
        """
        Receive data to the agent subprocess

        Parameters:
            turn (int): the current turn

        Returns:
            the agent output, an action to carry out
        """
        if self.__terminated() or self.process.stdout is None:
            raise ConnectionError(f"Cannot send data to agent {self.id}")

        if stderr := self.__read_stderr_non_blocking():
            log.debug(f"--- {self.name} stderr\n{stderr.strip()}\n" +
                      f"--- end of {self.name} stderr")

        timeout = Agent.TURN_TIMEOUT_S if turn > 0 else Agent.INITIAL_TIMEOUT_S
        if sys.platform == 'win32':
            return self.output_queue.get(timeout=timeout).strip()
        else:
            ready_to_read, _, _ = select([self.process.stdout.fileno()], [], [], timeout)
            if ready_to_read:
                if output := self.process.stdout.readline():
                    return str(output).strip()
        log.warning(f"{self.name} is disqualified for not providing output in time")
        return ""

    def __read_stderr_non_blocking(self) -> str | None:
        if not self.__terminated() and self.process.stderr is not None:
            if sys.platform == 'win32':
                stderr_lines = []
                while True:
                    try:
                        stderr_lines.append(self.error_queue.get_nowait())
                    except Empty:
                        break
                return "".join(stderr_lines)
            else:
                try:
                    output = ""
                    while select([self.process.stderr], [], [], 0)[0]:
                        if line := self.process.stderr.readline():
                            output += line
                    return output
                except (IOError, OSError) as e:
                    log.warning(f"Error reading stderr from agent {self.id}: {e}")
        return None

    @override
    def terminate(self):
        """Terminate the agent subprocess"""
        if not self.__terminated():
            try:
                self.process.terminate()
                self.process.wait(timeout=0.5)  # Give it a moment to terminate
            except TimeoutExpired:
                log.warning(f"Agent {self.id} did not terminate gracefully, killing")
                self.process.kill()
            except Exception as e:
                log.error(f"Error during agent {self.id} termination: {e}")
            self.process = None
            log.debug(f"Agent {self.id} terminated")


class PlaceBomb(Predicate):
    predicate_name = "placeBomb"

    def __init__(self, x=None, y=None):
        super().__init__(["x", "y"])
        self.x = x
        self.y = y

    def set_x(self, x):
        self.x = x

    def get_x(self):
        return self.x

    def set_y(self, y):
        self.y = y

    def get_y(self):
        return self.y


class Move(Predicate):
    predicate_name = "move"

    def __init__(self, x=None, y=None):
        super().__init__(["x", "y"])
        self.x = x
        self.y = y

    def set_x(self, x):
        self.x = x

    def get_x(self):
        return self.x

    def set_y(self, y):
        self.y = y

    def get_y(self):
        return self.y


ASPMapper.get_instance().register_class(PlaceBomb)
ASPMapper.get_instance().register_class(Move)


class AspAgent(Agent):
    """
    An agent that gets the next action to perform by solving an
    Answer Set Programming program.
    The ASP program is made of some facts about the game state and of some
    program files.

    The ASP program is provided with the following facts at every turn:

        % initial facts, these do not change
        cell(X, Y). % represents a grid cell
        myId(ID). % the agent's own ID
        gridSize(Width, Height).
        bombRange(3). % bomb explosion propagation range

        % facts modeling the game state at the beginning of the turn
        box(X, Y). % a box placed on the grid
        player(ID, X, Y, BombsLeft). % a player on the grid, BombsLeft is either 0 or 1
        bomb(OwnerID, X, Y, TurnsLeft). % a bomb on the grid, TurnsLeft is the detonation timer

    The output of the program may consist of one of two actions each turn:

        placeBomb(X, Y). % places a bomb at the current position and
                         % starts moving toward (X, Y) in the same turn
        move(X, Y). % moves one cell closer to (X, Y)
    """

    def __init__(self, agent_id: int, start_cell: tuple[int, int], asp_programs: list[str], name: str = ""):
        super().__init__(agent_id, start_cell, name)

        dlv_lib = 'dlv2'
        if sys.platform == 'win32':
            dlv_lib += '.exe'
        elif sys.platform == 'darwin':
            dlv_lib = '.max_5'

        self.handler = DesktopHandler(DLV2DesktopService(os.path.join("lib", dlv_lib)))
        self.handler.add_option(OptionDescriptor("--silent"))
        self.handler.add_option(OptionDescriptor("--filter=move/2,placeBomb/2"))
        self.handler.add_option(OptionDescriptor("--printonlyoptimum"))

        self.turn_state_program = ASPInputProgram()
        self.handler.add_program(self.turn_state_program)  # key = 0

        files = ASPInputProgram()
        self.handler.add_program(files)  # key = 1
        for filename in asp_programs:
            with open(filename) as program:
                files.add_program(program.read())

        self.answer_sets: AnswerSets | None = None
        self.worker = Thread(target=self.__main, daemon=True)
        self.lock = Lock()
        self.run_condition = Condition(self.lock)
        self.is_running = False
        self.worker.start()

    def __main(self):
        log.debug(f"Started {self.name} ({self.worker.name})")
        while True:
            with self.lock:
                while not self.is_running:
                    self.run_condition.wait()

            self.answer_sets = self.handler.start_sync()

            with self.lock:
                self.is_running = False
                self.run_condition.notify()

    @override
    def _serialize_turn_state(self,
                              agents: list[Agent],
                              bombs: list[Bomb],
                              grid: list[list[str]]) -> str:
        return "".join(
            [f"box({x},{y})." for y in range(len(grid)) for x in range(len(grid[y])) if
             grid[y][x] == CellType.BOX.value] +
            [f"player({a.id},{a.x},{a.y},{a.bombs_left})." for a in agents] +
            [f"bomb({b.owner_id},{b.x},{b.y},{b.timer})." for b in bombs]
        )

    @override
    def send_prelude(self, width: int, height: int):
        #  The param2 is not useful for the current league, and will always be:
        #     For players: explosion range of the player's bombs (= 3).
        #     For bombs: explosion range of the bomb (= 3).

        prelude = ASPInputProgram()
        prelude.add_program(
            f"gridSize({width},{height}). myId({self.id}). "
            + f"cell(0..{width - 1},0..{height - 1}). bombRange(3).")
        self.handler.add_program(prelude)  # key = 2

    @override
    def send_turn_state(self, agents: list[Agent], bombs: list[Bomb], grid: list[list[str]]):
        self.turn_state_program.set_programs(self._serialize_turn_state(agents, bombs, grid))

        with self.lock:
            self.is_running = True
            self.run_condition.notify()

    @override
    def receive(self, turn: int) -> str:
        timer = Timer(Agent.TURN_TIMEOUT_S if turn > 0 else Agent.INITIAL_TIMEOUT_S, self.__timeout)
        timer.start()
        with self.lock:
            while self.is_running and not self.disqualified:
                self.run_condition.wait()
        timer.cancel()

        if self.disqualified:
            log.warning(f"{self.name} is disqualified because it did not respond in time")
            return ""

        if err := self.answer_sets.get_errors():
            log.debug(self.handler.get_input_program(0).get_programs()
                      + self.handler.get_input_program(1).get_programs()
                      + self.handler.get_input_program(2).get_programs())
            log.error(err)
            return ""

        # Cfr. handler options. Gives only the optimum and can either contain
        # placeBomb/2 or move/2. If contains neither it's invalid.

        for atom in self.answer_sets.get_answer_sets()[0].get_atoms():
            if isinstance(atom, Move):
                return f"MOVE {atom.x} {atom.y}"
            else:
                return f"BOMB {atom.x} {atom.y}"
        log.debug(f"{self.name} provided an empty answer set")
        return ""

    def __timeout(self):
        with self.lock:
            self.disqualified = True
            self.run_condition.notify()
