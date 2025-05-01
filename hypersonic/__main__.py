"""
This is a runner for the Hypersonic challenge.
The complete specification of the game can be found here

              https://www.codingame.com/ide/puzzle/hypersonic
"""
from time import time
import sys
import pygame
import os

from .display import Display
from .model import Game
from .entities import ExecutableAgent, AspAgent


def main():
    model_update_rate = 2  # turns per second
    assert model_update_rate < 10, "Logic update rate must give the agents at least 100ms per turn"
    model_update_interval = 1 / model_update_rate
    model_accumulator = 0.0
    last_time = time()

    game = Game([
        ExecutableAgent(0, Game.START_POSITIONS[0], [sys.executable, os.path.join("encodings", "random_agent.py")], "Random"),
        AspAgent(1, Game.START_POSITIONS[1], [os.path.join("encodings", "test")], "AspAgent")
    ])
    display = Display(game)
    clock = pygame.time.Clock()

    while True:
        current_time = time()
        delta_time = current_time - last_time
        last_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                for agent in game.agents:
                    agent.terminate() # otherwise leaves zombie processes
                pygame.quit()
                print("Exiting. Bye!")
                return
            display.handle(event, game)

        if game.running and not game.paused:
            model_accumulator += delta_time
            while model_accumulator >= model_update_interval:
                game.update()
                display.explosion_frame = 0
                model_accumulator -= model_update_interval

        display.draw(delta_time, model_accumulator * model_update_rate)
        clock.tick(Display.FRAME_RATE)


if __name__ == "__main__":
    main()
