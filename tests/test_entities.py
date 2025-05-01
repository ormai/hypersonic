from hypersonic.entities import Agent, AspAgent
from time import time


def test_asp_agent_timeout():
    agent = AspAgent(0, (0, 0), [])
    agent.send_turn_state([], [], [])
    agent.turn_state_program.add_program("""
        thing(0..200).
        { do(Thing) : thing(Thing) }.
        n(N) :- N = #max { Thing : do(Thing) }.""")
    start = time()
    assert agent.receive(1) == "", "Time out works"
    assert agent.disqualified, "Not providing output in time is a loose condition"
    assert time() - start > Agent.TURN_TIMEOUT_S


def test_asp_agent_output_well_formed_move_action():
    agent = AspAgent(0, (0, 0), [])
    agent.send_turn_state([], [], [])
    agent.turn_state_program.add_program("move(5, 6).")
    assert agent.receive(1) == "MOVE 5 6"
    assert not agent.disqualified


def test_asp_agent_output_well_formed_place_bomb_action():
    agent = AspAgent(0, (0, 0), [])
    agent.send_turn_state([], [], [])
    agent.turn_state_program.add_program("placeBomb(5, 6).")
    assert agent.receive(1) == "BOMB 5 6"
    assert not agent.disqualified


def test_asp_agent_malformed_output():
    agent = AspAgent(0, (0, 0), [])
    agent.send_turn_state([], [], [])
    assert agent.receive(1) == ""

    agent.send_turn_state([], [], [])
    agent.turn_state_program.add_program("something.")
    assert agent.receive(1) == ""
