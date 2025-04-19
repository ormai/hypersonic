class Explosion:
    TICK_DURATION = 2

    def __init__(self, x: int, y: int, duration=TICK_DURATION):
        self.x = x
        self.y = y
        self.timer = duration

    def tick(self):
        self.timer -= 1
        return self.timer > 0
