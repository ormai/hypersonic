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
    agent_script = os.path.join("game", "agents", "random_agent.py")
    game = Game([
        ExecutableAgent(0, Game.START_POSITIONS[0], [sys.executable, agent_script], "Random1"),
        #ExecutableAgent(1, Game.START_POSITIONS[1], [sys.executable, agent_script], "Random2")
        AspAgent(1, Game.START_POSITIONS[1], [os.path.join("game", "encodings", "test")], "AspAgent")
    ])
    display = Display(game)
    clock = pygame.time.Clock()

    model_update_rate = 4
    model_update_interval = 1 / model_update_rate
    model_accumulator = 0.0
    frame_rate = 30
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
                    sys.exit()
                case pygame.MOUSEBUTTONDOWN | pygame.MOUSEBUTTONUP:
                    if display.start_button.is_clicked(event.pos, event.button == 1):
                        paused = False
                    if display.pause_button.is_clicked(event.pos, event.button == 1):
                        paused = True
                case pygame.MOUSEMOTION:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if display.start_button.is_hover(
                        event.pos) or display.pause_button.is_hover(event.pos) else pygame.SYSTEM_CURSOR_ARROW)

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

        display.draw()
        clock.tick(frame_rate)


if __name__ == "__main__":
    main()
