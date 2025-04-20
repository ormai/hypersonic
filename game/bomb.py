from game.enums import EntityType


class Bomb:
    def __init__(self, owner_id, x, y, timer, bomb_range):
        self.owner_id = owner_id
        self.x = x
        self.y = y
        self.timer = timer
        self.range = bomb_range
        self.exploded = False

    def __repr__(self):
        return f"Bomb(owner={self.owner_id}, pos=({self.x},{self.y}), timer={self.timer}, range={self.range})"

    def tick(self) -> bool:
        """
        Decreases the bomb timer by one

        Returns:
            (bool): whether the bomb should explode in this round
        """
        if self.timer > 0:
            self.timer -= 1
        return self.timer == 0

    def serialize(self):
        # entity_type owner x y param_1 param_2
        # param_1 = timer, param_2 = range
        return f"{EntityType.BOMB.value} {self.owner_id} {self.x} {self.y} {self.timer} {self.range}"
