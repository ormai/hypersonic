width, height, my_id = map(int, input().split())

while True:
    for _ in range(height):
        row = input()
        assert len(row) == 13
    for _ in range(int(input())):
        state = input()

    print("BOMB 6 5")
