from time import time
import sys
import pygame
import os

from .display import Display
from .model import Game
from .entities import ExecutableAgent, AspAgent


active_agents = ['randomASP', 'randomPY']

if len(active_agents) > 2:
    raise ValueError(f"Too many agents. Maximum allowed: 2")

AGENTS = {
    'iPuponi': AspAgent(agent_id=active_agents.index('iPuponi')
                            if 'iPuponi' in active_agents else 0,
                            start_cell=Game.START_POSITIONS[active_agents.index('iPuponi')]
                            if 'iPuponi' in active_agents else (0, 0),
                            asp_programs=[os.path.join("encodings", "iPuponi.lp")],
                            name="iPuponi"),
    'nASPi': AspAgent(agent_id=active_agents.index('nASPi')
                        if 'nASPi' in active_agents else 0,
                        start_cell=Game.START_POSITIONS[active_agents.index('nASPi')]
                        if 'nASPi' in active_agents else (0, 0),
                        asp_programs=[],
                        name="nASPi"),
    'leo_sal': AspAgent(agent_id=active_agents.index('leo_sal')
                            if 'leo_sal' in active_agents else 0,
                            start_cell=Game.START_POSITIONS[active_agents.index('leo_sal')]
                            if 'leo_sal' in active_agents else (0, 0),
                            asp_programs=[],
                            name="leo_sal"),
    'gameStoppers': AspAgent(agent_id=active_agents.index('gameStoppers')
                                if 'gameStoppers' in active_agents else 0,
                                start_cell=Game.START_POSITIONS[active_agents.index('gameStoppers')]
                                if 'gameStoppers' in active_agents else (0, 0),
                                asp_programs=[],
                                name="gameStoppers"),
    'randomASP': AspAgent(agent_id=active_agents.index('randomASP')
                            if 'randomASP' in active_agents else 0,
                            start_cell=Game.START_POSITIONS[active_agents.index('randomASP')]
                            if 'randomASP' in active_agents else (0, 0),
                            asp_programs=[os.path.join("encodings", "random.lp")],
                            name="randomASP"),
    'randomPY': ExecutableAgent(agent_id=active_agents.index('randomPY')
                                    if 'randomPY' in active_agents else 0,
                                    start_cell=Game.START_POSITIONS[active_agents.index('randomPY')]
                                    if 'randomPY' in active_agents else (0, 0),
                                    cmd=[sys.executable, os.path.join("encodings", "random_agent.py")],
                                    name="randomPY")
}

def main():
    model_update_rate = 2  # turns per second
    model_update_interval = 1 / model_update_rate
    model_accumulator = 0.0
    last_time = time()

    game = Game([AGENTS[agent] for agent in active_agents])
    display = Display(game)
    clock = pygame.time.Clock()

    while True:
        current_time = time()
        delta_time = current_time - last_time
        last_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                for agent in game.agents:
                    agent.terminate()  # otherwise leaves zombie processes
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


main()
