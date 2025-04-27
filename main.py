"""
This is a runner for the Hypersonic challenge.
The complete specification of the game can be found here

              https://www.codingame.com/ide/puzzle/hypersonic
"""
from time import time
import sys
import pygame
import os

from game.display import Display
from game.model import Game
from game.entities import ExecutableAgent, AspAgent


def main():
    game = Game([
        ExecutableAgent(0, Game.START_POSITIONS[0], [sys.executable, os.path.join("game", "agents", "random_agent.py")],
                        "Random"),
        AspAgent(1, Game.START_POSITIONS[1], [os.path.join("game", "encodings", "test")], "AspAgent")
    ])
    display = Display(game)
    clock = pygame.time.Clock()

    model_update_rate = 3
    model_update_interval = 1 / model_update_rate
    model_accumulator = 0.0
    last_time = time()

    paused = True
    while True:
        current_time = time()
        delta_time = current_time - last_time
        last_time = current_time

        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    pygame.quit()
                    print("Exiting. Bye!")
                    return
                case pygame.MOUSEBUTTONDOWN | pygame.MOUSEBUTTONUP:
                    paused = (paused and not display.start_button.is_clicked(event.pos, event.button == 1)
                              or not paused and display.pause_button.is_clicked(event.pos, event.button == 1))
                case _:
                    display.handle(event)

        if game.running:
            model_accumulator += delta_time
            while model_accumulator >= model_update_interval:
                if not paused:
                    for agent in game.agents:
                        agent.send_turn_state(game.agents, game.bombs, game.grid)

                    actions = {agent.id: agent.receive(game.turn) for agent in game.agents}
                    for agent in game.agents:
                        if agent.timed_out:
                            # TODO: handle defeat
                            game.running = False
                    game.update(actions)

                if game.turn >= Game.MAX_TURNS:
                    for agent in game.agents:
                        agent.terminate()
                    game.running = False
                model_accumulator -= model_update_interval

        display.draw(model_accumulator * model_update_rate, paused)
        clock.tick(Display.FRAME_RATE)


if __name__ == "__main__":
    main()
