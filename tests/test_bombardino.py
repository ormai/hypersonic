"""Correctens, performance, optimality tests for Bombardino, the bot."""

import pytest
import os
from hypersonic.model import Game
from hypersonic.entities import Bombardino, AspAgent
from hypersonic.layouts import LAYOUTS


@pytest.fixture(autouse=True)
def game():
    agent = Bombardino(0, (0, 0), [os.path.join("encodings", "bombardino.lp")])
    enemy = AspAgent(1, (12, 10), [])
    enemy.handler.get_input_program(1).add_program("move(12, 10).")  # dummy
    _game = Game([agent, enemy])
    _game.grid = [list(row) for row in LAYOUTS[0]]  # can't have randomness here
    yield _game


def test_does_not_wait_after_placing_bomb(game: Game):
    for _ in range(6):
        game.update()
    # First optimum position is (1, 5), second is at (6, 5), third at (11, 5)
    # Precondition: agent goes to (1, 5) in 6 turns
    assert (game.agents[0].x, game.agents[0].y) == (1, 5), "optimum reached"
    game.update()  # turn 6 -> turn 7

    # At the seventh turn the agent outputs `BOMB 5 8`
    assert any((bomb.x, bomb.y) == (1, 5) for bomb in game.bombs), "bomb paced"
    assert (game.agents[0].x, game.agents[0].y) == (1, 6), "moves immediately"

    for _ in range(8):  # 7 turns to move, 1 waiting for the bomb to explode
        game.update()
    assert any((bomb.x, bomb.y) == (6, 5) for bomb in game.bombs), "bomb paced"
    assert (game.agents[0].x, game.agents[0].y) == (6, 6), "moves immediately"

    for _ in range(8):
        game.update()
    assert any((bomb.x, bomb.y) == (11, 5) for bomb in game.bombs), "bomb paced"
    assert (game.agents[0].x, game.agents[0].y) == (10, 5), "moves immediately"



def test_stays_put_when_it_reaches_the_optimum_but_has_not_the_bomb(game: Game):
    """
    Check for an issue that causes the agent to go back and forth when it
    reaches the optimum position but has to wait to get back the bomb.
    """
    for _ in range(6):
        game.update()
    assert game.agents[0].bombs_left == 1, "not placed yet"
    game.agents[0].bombs_left = 0
    for _ in range(8):
        game.update()
        assert (game.agents[0].x, game.agents[0].y) == (1, 5), "doesn't move"
