from subprocess import Popen, PIPE, TimeoutExpired
from select import select
from game.enums import EntityType
from time import time


class Agent:
    """
    An agent is a subprocess executing on its own. It gets the game state from
    the game via stdin and outputs a move via stdout. For instance, it can be
    a python script or an ASP program run by DLV2.

    This class also represents the concept of a Player.
    """

    INITIAL_TIMEOUT_S = 1.0
    TURN_TIMEOUT_S = 0.1

    def __init__(self, agent_id: int, start_cell: tuple[int, int], cmd: list[str], name: str = ""):
        """
        Parameters:
            cmd (str): the command for the subprocess, each word split
            agent_id (int): an identifier for the agent
        """
        self.id = agent_id
        self.x, self.y = start_cell
        self.bombs_left = 1
        self.bomb_range = 3  # Default range including center
        self.is_alive = True
        self.last_action = ""
        self.message = ""
        self.name = f"Agent {agent_id}" if not name else name
        self.cmd = cmd
        self.process: Popen | None = Popen(
            self.cmd,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            bufsize=0,
            universal_newlines=True,
        )
        print(f"Started {agent_id} (PID: {self.process.pid}): {' '.join(self.cmd)}")

    def __terminated(self) -> bool:
        """Check if the underlying subprocess has terminated"""
        return self.process is None or self.process.poll() is not None

    def send(self, data: str) -> None:
        """
        Send data to the agent subprocess

        Parameters:
            data (str): line of text to send

        Returns:
            bool: whether then sending was successful
        """
        if self.__terminated() or self.process.stdin is None:
            raise ConnectionError(f"Cannot send data to agent {self.id}")

        try:
            self.process.stdin.write(data + "\n")
            self.process.stdin.flush()
        except (IOError, BrokenPipeError, OSError) as e:
            raise ConnectionError(f"Error sending data to agent {self.id}: {e}")

    def receive(self, turn: int) -> str:
        """
        Send data to the agent subprocess

        Parameters:
            turn (int): the current turn

        Returns:
            the agent output
        """
        if self.__terminated() or self.process.stdout is None:
            raise ConnectionError(f"Cannot send data to agent {self.id}")

        if __debug__ and (stderr := self.__read_stderr_non_blocking()):
            print(f"--- Agent {self.id} stderr",
                  stderr.strip(),
                  f"---end of agent {self.id} stderr", sep="\n")

        # Response time per turn ≤ 100 ms
        # Response time for the first turn ≤ 1000 ms
        timeout = self.TURN_TIMEOUT_S if turn > 0 else self.INITIAL_TIMEOUT_S
        start_time = time()
        while time() - start_time < timeout:
            if line := self.process.stdout.readline():
                return str(line).strip()
            raise ConnectionError(f"{self.id}'s stdout closed (EOF)")
        raise TimeoutError(f"Agent {self.id} failed to provide output in time")

    def __read_stderr_non_blocking(self) -> str | None:
        if not self.__terminated() and self.process.stderr is not None:
            try:
                output = ""
                while select([self.process.stderr], [], [], 0)[0]:
                    if line := self.process.stderr.readline():
                        output += line
                return output
            except (IOError, OSError) as e:
                print(f"Error reading stderr from agent {self.id}: {e}")
        return None

    def terminate(self) -> None:
        """Terminate the agent subprocess"""
        if not self.__terminated():
            try:
                self.process.terminate()
                self.process.wait(timeout=0.5)  # Give it a moment to terminate
            except TimeoutExpired:
                print(f"Agent {self.id} did not terminate gracefully, killing")
                self.process.kill()
            except Exception as e:
                print(f"Error during agent {self.id} termination: {e}")
            self.process = None
            print(f"Agent {self.id} terminated")

    def serialize(self) -> str:
        """Format the entity data to pass it to the agents via stdin"""
        return f"{EntityType.AGENT.value} {self.id} {self.x} {self.y} {self.bombs_left} {self.bomb_range}"
