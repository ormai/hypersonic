width, height, my_id = map(int, input().split())

turn = 0

actions = ["MOVE 0 2", "MOVE 0 2", "BOMB 0 0", "MOVE 0 0", "MOVE 0 2", "MOVE 0 2"]

while True:
    for _ in range(height):
        row = input()
        assert len(row) == 13

    for _ in range(int(input())):
        state = input()

    if turn < 6:
        print(actions[turn])
    else:
        print("BOMB 6 5")
    turn += 1