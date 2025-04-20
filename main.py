import sys

import pygame

from game.display import Display
from game.model import Game, get_initial_input_string


def main():
    # FIXME: Non è chiaro al momento come passare stdin a un programma asp e ricevere stdout.
    # FIXME: Inoltre l'agente dovrebbe avere un loop infinito e non terminare.
    # FIXME: Questi dettagli solo lasciati da determinare.

    # I comandi degli agenti da eseguire in co-processi.
    game = Game([
        [sys.executable, "agents/random_agent.py"],
        [sys.executable, "agents/other_random_agent.py"]
    ])
    display = Display(game)
    clock = pygame.time.Clock()

    for agent in game.agents:
        agent.send(get_initial_input_string(agent.id))

    while game.running:
        if any(event.type == pygame.QUIT for event in pygame.event.get()):
            bail_out()

        for agent in game.agents:
            agent.send(game.get_serialized_game_state())

        current_timeout = game.TIMEOUT_PER_TURN if game.turn > 0 else game.TIMEOUT_FIRST_TURN
        actions: list[str] = ["" for _ in range(len(game.agents))]
        for agent in game.agents:
            actions[agent.id] = agent.receive(current_timeout)
        print(actions)
        game.update(actions)

        display.draw()
        clock.tick(4)
        game.turn += 1
        if game.turn >= game.MAX_TURNS:
            game.running = False

    print("Game ended")
    for agent in game.agents:
        agent.terminate()

    survivors = game.alive_agents()
    display.show_final_message(f"Winner: agent {survivors[0].id}" if len(survivors) == 1 else "Draw")

    while pygame.event.wait().type != pygame.QUIT:
        pass
    bail_out()


def bail_out():
    pygame.quit()
    print("Exiting. Bye!")
    sys.exit()


if __name__ == "__main__":
    main()
