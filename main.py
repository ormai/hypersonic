"""
This is a runner for the Hypersonic challenge. The agents are provided
as isolated programs run in subprocesses. The agents and the runner (this
program) comunicate through the standard input stream and the standard
output stream.

The complete specification of the game and message formats can be found here

              https://www.codingame.com/ide/puzzle/hypersonic
"""

from game.display import Display
from game.model import Game
import sys
import pygame


# FIXME: Non è chiaro al momento come passare stdin a un programma asp e ricevere stdout.
# FIXME: Inoltre l'agente dovrebbe avere un loop infinito e non terminare.
# FIXME: Questi dettagli solo lasciati da determinare.

def main():
    game = Game([
        ("Random1", [sys.executable, "game/agents/random_agent.py"]),
        ("Random2", [sys.executable, "game/agents/other_random_agent.py"])
    ])
    display = Display(game)
    clock = pygame.time.Clock()

    # TODO: start button here

    for agent in game.agents:
        agent.send(game.prelude(agent.id))

    while game.running:
        if any(event.type == pygame.QUIT for event in pygame.event.get()):
            bail_out()

        for agent in game.agents:
            agent.send(game.turn_state())

        game.update({agent.id: agent.receive(game.turn) for agent in game.agents})
        display.draw()
        clock.tick(30)  # simulation speed, updates per second
        game.turn += 1
        if game.turn >= Game.MAX_TURNS:
            game.running = False

    print("Game ended")
    for agent in game.agents:
        agent.terminate()

    display.show_final_message(
        f"Winner: {max((agent for agent in game.agents), key=lambda a: a.boxes_destroyed).name}"
        if len(set([agent.boxes_destroyed for agent in game.agents])) != 1
        else "Draw")
    print(set(agent.boxes_destroyed for agent in game.agents), len(set(agent.boxes_destroyed for agent in game.agents)))

    while pygame.event.wait().type != pygame.QUIT:
        pass
    bail_out()


def bail_out():
    pygame.quit()
    print("Exiting. Bye!")
    sys.exit()


if __name__ == "__main__":
    main()
