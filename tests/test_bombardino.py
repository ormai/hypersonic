"""Correctens, performance, optimality tests for Bombardino, the bot."""

import pytest
import os
from hypersonic.model import Game, CellType
from hypersonic.entities import Bombardino, AspAgent, Bomb
from hypersonic.layouts import LAYOUTS
from .test_model import EMPTY_GRID


@pytest.fixture(autouse=True)
def game():
    agent = Bombardino(0, (0, 0), [os.path.join("encodings", "bombardino")])
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


def test_protects_itself_against_box_stealing(game: Game):
    game.grid = [list(row) for row in EMPTY_GRID]
    game.grid[5][5] = CellType.BOX.value
    # Without a real thread protection doesn't trigger
    game.agents[1] = Bombardino(1, Game.START_POSITIONS[1], [os.path.join("encodings", "bombardino.lp")])
    game.agents[1].send_prelude(game.WIDTH, game.HEIGHT)

    # The enemy stays at (12, 10) the whole time
    # It takes 11 turns for the enemy to place a bomb that threatens the box

    # The agent takes 10 + 8 turns to take out the box

    for _ in range(10):
        game.update()

    assert abs(game.bombs[0].x - 5) + abs(game.bombs[0].y - 5) == 1, "bomb is placed next to the box"


def test_chooses_suboptimal_when_enemy_is_closer_to_optimal_and_has_bomb(game: Game):
    # If enemy stays still the agent will choose the actual best
    game.agents[1] = Bombardino(1, Game.START_POSITIONS[1], [os.path.join("encodings", "bombardino.lp")])
    game.agents[1].send_prelude(game.WIDTH, game.HEIGHT)

    game.grid = [list(row) for row in EMPTY_GRID]
    game.grid[5][2] = CellType.BOX.value # second choice
    game.grid[5][10] = game.grid[7][8] = CellType.BOX.value
    # (8, 5) is the best position

    for _ in range(6):
        game.update()
    assert any(bomb for bomb in game.bombs if (bomb.x, bomb.y) in ((0, 5), (2, 3))), "places bomb where it supposed to"

    # Agent is closer but gets bomb after enemy
    game.grid = [list(row) for row in EMPTY_GRID]


def test_chooses_suboptimal_when_it_is_closer_but_enemy_has_smaller_bomb_cooldown(game: Game):
    game.agents[1] = Bombardino(1, (12, 7), [os.path.join("encodings", "bombardino.lp")])
    game.agents[1].send_prelude(game.WIDTH, game.HEIGHT)
    game.agents[0].bombs_left = 0
    game.bombs.append(Bomb(0, Game.WIDTH - 1, 0))
    game.agents[0].x, game.agents[0].y = 6, 3

    game.grid = [list(row) for row in EMPTY_GRID]
    game.grid[5][2] = CellType.BOX.value
    game.grid[2][11] = game.grid[4][9] = CellType.BOX.value
    # (9, 2) is the best position
    # Agent's distance is 2 turns, enemy's distance is 7 turns

    for _ in range(Bomb.LIFETIME):
        game.update()

    assert any(bomb for bomb in game.bombs if (bomb.x, bomb.y) in ((3, 5), (2, 4))), "places bomb where it is supposed to"
