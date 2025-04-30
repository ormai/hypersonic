import pytest

import sys

print(sys.path)

from hypersonic.model import Game
from hypersonic.entities import Bomb, AspAgent, CellType


@pytest.fixture(autouse=True)
def game():
    _game = Game([AspAgent(i, Game.START_POSITIONS[i], []) for i in range(2)])
    _game.grid = [list(row) for row in [
        ".............",
        ".............",
        ".............",
        ".............",
        ".............",
        ".............",
        ".............",
        ".............",
        ".............",
        ".............",
        "............."
    ]]
    yield _game


def test_tick_bombs(game: Game):
    bomb = Bomb(0, 9, 5, Game.BOMB_LIFETIME, 3)
    game.bombs = [bomb]
    for i in range(Game.BOMB_LIFETIME - 1, 0, -1):
        assert len(game.tick_bombs()) == 0, "No explosions yet"
        assert bomb.timer == i, "Timer decreases at each tick"
    assert game.tick_bombs() == [bomb], "Returns exploded bombs"
    assert len(game.bombs) == 0, "Exploded bombs get removed from the game"


def test_propagate_explosion(game: Game):
    bomb = Bomb(0, 3, 7, 0, 3)
    assert len(game.explosions) == 0, "Initially, there are no explosion"
    game.propagate_explosions([bomb])
    assert (bomb.x, bomb.y) in game.explosions, "Bomb location becomes an explosion"
    assert game.explosions == {(bomb.x, bomb.y), (bomb.x + 1, bomb.y), (bomb.x + 2, bomb.y), (bomb.x - 1, bomb.y),
                               (bomb.x - 2, bomb.y), (bomb.x, bomb.y + 1), (bomb.x, bomb.y + 2), (bomb.x, bomb.y - 1),
                               (bomb.x, bomb.y - 2)}, "Explosion propagates"


def test_propagate_explosion_chain_reaction(game: Game):
    first, second = Bomb(0, 4, 5, 0, 3), Bomb(1, 4, 7, 8, 3)
    game.bombs = [second]
    game.propagate_explosions([first])
    assert game.bombs == [] and (second.x, second.y) in game.explosions, "Second bomb gets detonated by the first"


def test_propagate_explosion_destroys_boxes(game: Game):
    bx, by = 6, 6
    boxes = ((bx, by + 2), (bx, by - 2), (bx + 2, by), (bx - 2, by))
    for x, y in boxes:
        game.grid[y][x] = CellType.BOX.value
    game.propagate_explosions([Bomb(0, bx, by, 0, 3)])
    assert all(game.grid[y][x] == CellType.FLOOR.value for x, y, in boxes), "All boxes get destroyed"

    boxes = ((bx, by + 1), (bx, by + 2))
    for x, y in boxes:
        game.grid[y][x] = CellType.BOX.value
    game.propagate_explosions([Bomb(0, bx, by, 0, 3)])
    assert game.grid[by + 1][bx] == CellType.FLOOR.value, "Box closest to the explosion gets destroyed"
    assert game.grid[by + 2][bx] == CellType.BOX.value, "Explosion propagation stops after a box gets hit"


def test_path(game: Game):
    for x in range(12, 0, -1):
        next_cell = game.path((5, x), (5, 0))
        assert next_cell is not None, "Path exists"
        assert next_cell[1] == x - 1, "Should find the next cell to get closer to the destination"
    assert game.path((5, 0), (5, 0)) is None, "There is no path to go where you already are"


def test_path_when_blocked(game: Game):
    # 0 . .
    # P 0 X
    # 0 . .
    #
    # P: player, 0: box, X: destination
    for x, y in ((0, 4), (1, 5), (0, 6)):
        game.grid[y][x] = CellType.BOX.value
    assert game.path((5, 0), (5, 2)) is None, "There is no path if there is a block between source and destination"


def test_path_when_dst_is_blocked(game: Game):
    game.grid[10][12] = CellType.BOX.value
    assert game.path((0, 0), (10, 12)) is None, "There is no path when the destination is not walkable"


def test_walkable(game: Game):
    assert (not game.walkable(Game.WIDTH * 2, Game.HEIGHT - 1)
            and not game.walkable(Game.WIDTH - 1, Game.HEIGHT * 2)
            and not game.walkable(Game.WIDTH * -2, 0)
            and not game.walkable(0, Game.HEIGHT * -2)), "Bounds are checked"

    game.bombs = [Bomb(0, 5, 6, 8, 3)]
    assert game.walkable(5, 6), "Cells containing bombs placed in the current turn are walkable"
    game.tick_bombs()
    assert not game.walkable(5, 6), "Cells containing bombs placed in previous turns aren not walkable"

    game.grid[8][9] = CellType.BOX.value
    assert not game.walkable(9, 8), "Cells containing boxes are not walkable"

    assert all(game.walkable(x, y) for y in range(Game.HEIGHT) for x in range(Game.WIDTH) if
               (x, y) != (5, 6) and (x, y) != (9, 8)), "Every other cell is walkable"


def test_process_agent_actions(game: Game):
    previous_player_pos = game.agents[1].x, game.agents[1].y
    next_expected_player_pos1 = game.path(previous_player_pos[::-1], (6, 5))[::-1]  # type: ignore
    next_expected_player_pos0 = game.path((game.agents[0].y, game.agents[0].x), (4, 3))

    game.process_agent_actions({0: "MOVE 3 4", 1: "BOMB 5 6"})

    current_player_pos = game.agents[1].x, game.agents[1].y
    bomb_pos = game.bombs[0].x, game.bombs[0].y
    assert (bomb_pos == previous_player_pos and current_player_pos == next_expected_player_pos1), \
        "'BOMB x y' places a bomb in the current agent position and starts moving towards (x, y)"
    assert next_expected_player_pos0 == (game.agents[0].y,
                                         game.agents[0].x), "'MOVE x y' makes the agent move one cell towards (x, y)"


def test_move(game: Game):
    prev_x, prev_y = game.agents[0].x, game.agents[0].y
    game.move(game.agents[0], game.agents[0].x, game.agents[0].y)
    assert game.agents[0].x == prev_x and game.agents[
        0].y == prev_y, "If the agent wants to move to its own current position, noting happens"

    game.grid[1][3] = CellType.BOX.value
    for i in range(1 + 3):
        game.move(game.agents[0], 3, 1)
    assert (game.agents[0].x, game.agents[0].y) == (3, 0), \
        "Moving to a cell that is not walkable causes a fall back to a valid adjacent cell as the destination"

    game.move(game.agents[0], 4, 0)
    assert (game.agents[0].x, game.agents[0].y) == (4, 0), "Move happens when there is no problem"
