from random import randint

width, height, my_id = map(int, input().split())

turn = 0
turns_left = 0  # wait to reach the position
current_action = ""
while True:
    for _ in range(height):
        row = input()
        assert len(row) == 13

    x, y = 0, 0
    for _ in range(int(input())):
        entity_type, owner, x, y, param_1, param_2 = map(int, input().split())

    if turns_left <= 0:
        dst_x, dst_y = randint(0, width - 1), randint(0, height - 1)
        if randint(0, 1) == 1:
            current_action = f"MOVE {dst_x} {dst_y}"
        else:
            current_action = f"BOMB {dst_x} {dst_y}"
        turns_left = abs(dst_x - x) + abs(dst_y - y) / 3 * 2

    print(current_action)
    turn += 1
    turns_left -= 1
