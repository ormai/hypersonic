from enum import Enum

class CellType(Enum):
    EMPTY = "."
    BOX = "0"

class EntityType(Enum):
    AGENT = "0"
    BOMB = "1"

