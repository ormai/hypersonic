from game.display import Display
from game.model import Game
import sys
import pygame


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
        agent.send(game.get_serialized_prelude(agent.id))

    while game.running:
        if any(event.type == pygame.QUIT for event in pygame.event.get()):
            bail_out()

        for agent in game.agents:
            agent.send(game.get_serialized_turn_state())

        game.update({agent.id: agent.receive(game.turn) for agent in game.agents})
        display.draw()
        clock.tick(4)
        game.turn += 1
        if game.turn >= game.MAX_TURNS:
            game.running = False

    print("Game ended")
    for agent in game.agents:
        agent.terminate()

    survivors = game.alive_agents()
    display.show_final_message(f"Winner: {survivors[0].id}" if len(survivors) == 1 else "Draw")

    while pygame.event.wait().type != pygame.QUIT:
        pass
    bail_out()


def bail_out():
    pygame.quit()
    print("Exiting. Bye!")
    sys.exit()


if __name__ == "__main__":
    main()
