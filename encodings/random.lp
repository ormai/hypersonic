% Behave chaotically
destination(X, Y) :- gridSize(W, H), &rand(0, W - 1; X), &rand(0, H - 1; Y).
action(WhichOne) :- &rand(0, 1; WhichOne). % either move/1 or placeBomb/1
placeBomb(X, Y) :- destination(X, Y), action(0).
move(X, Y) :- destination(X, Y), action(1).

% Some assertions
:- gridSize(W, H), W <> 13, H <> 11.

:- bombRange(R), R <> 3.

atLeastOneBox :- box(_, _).
:- not atLeastOneBox.

atLeastOneCell :- cell(_, _).
:- not atLeastOneCell.

myPlayerExists :- myId(ID), player(ID, _, _, _).
:- not myPlayerExists.

:- gridSize(W, H), #count{X, Y : cell(X, Y)} = C, C <> W * H.

:~ dead. [1000@1]
