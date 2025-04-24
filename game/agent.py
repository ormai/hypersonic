from subprocess import Popen, PIPE, TimeoutExpired
from select import select
from time import time
from abc import ABC, abstractmethod
from typing import override

from game.enums import EntityType
from game.log import get_logger

log = get_logger(__name__)


class Agent(ABC):
    """An autonomous player"""

    INITIAL_TIMEOUT_S = 1.0  # Response time for the first turn ≤ 1000 ms
    TURN_TIMEOUT_S = 0.1  # Response time per turn ≤ 100 ms

    def __init__(self, agent_id: int, start_cell: tuple[int, int], name: str = ""):
        self.id = agent_id
        self.x, self.y = start_cell
        self.bombs_left = 1
        self.boxes_destroyed = 0
        self.bomb_range = 3  # Default range including center
        self.last_action = ""
        self.message = ""
        self.name = f"Agent {agent_id}" if not name else name

    @abstractmethod
    def send(self, data: str):
        pass

    @abstractmethod
    def receive(self, turn: int) -> str:
        pass

    def serialize(self) -> str:
        """Format the entity data to pass it to the agents via stdin"""
        return f"{EntityType.AGENT.value} {self.id} {self.x} {self.y} {self.bombs_left} {self.bomb_range}"

    def terminate(self):
        pass


class ExecutableAgent(Agent):
    """
    An executable agent is a subprocess executing on its own. It gets the game state from
    the runner via stdin and outputs an action via stdout. For instance, it can be
    a python script or a compiled C++ program, i.e. an executable
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
        log.debug(f"Started {agent_id} (PID: {self.process.pid}): {' '.join(cmd)}")

    def __terminated(self) -> bool:
        """Check if the underlying subprocess has terminated"""
        return self.process is None or self.process.poll() is not None

    @override
    def send(self, data: str):
        """
        Send data to the agent subprocess

        Args:
            data (str): line of text to send
        """
        if self.__terminated() or self.process.stdin is None:
            raise ConnectionError(f"Cannot send data to agent {self.id}")

        try:
            self.process.stdin.write(data + "\n")
            self.process.stdin.flush()
        except (IOError, BrokenPipeError, OSError) as e:
            raise ConnectionError(f"Error sending data to agent {self.id}: {e}")

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
        start_time = time()
        while time() - start_time < timeout:
            if line := self.process.stdout.readline():
                return str(line).strip()
            raise ConnectionError(f"Received EOF from {self.name}. Probably crashed.")

        # TODO: if this happens the agent should lose not crash the runner
        raise TimeoutError(f"{self.name} failed to provide output in time")

    def __read_stderr_non_blocking(self) -> str | None:
        if not self.__terminated() and self.process.stderr is not None:
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
