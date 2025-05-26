% =========================================
% Author: nASPi Team -> Alessandro Sidero, Lorenzo Giandomenico
% File: naspi_useful_preds
% Description: Defines basic predicates used throughout the agent logic.
% Includes player's position, bomb availability, free cells, movement directions,
% distance calculations and adjacency relations.
% Requirements:
% - Facts: cell/2, box/2, player/4, bomb/4, myId/1, explosionRange/1, blownUpBoxes/2
% - External pred: placeBomb/2, inExplosion/2
% - External function: &abs/2 for computing absolute values
% =========================================

% myPos(X,Y): current position of my player.
myPos(X,Y) :- player(ID,X,Y,_), myId(ID).

% haveBomb: true if my player has at least one bomb.
haveBomb :- player(ID,_,_,B), myId(ID), B > 0.

% bombPos(X,Y): position of any active bomb.
bombPos(X,Y) :- bomb(_,X,Y,_).

% cellFree(X,Y): a cell is free if it's not a box or a bomb.
cellFree(X,Y) :- cell(X,Y), not bombPos(X,Y), not box(X,Y).

% placed: true if a bomb has been placed.
placed :- placeBomb(_,_).

% delta(Dir,DX,DY): vector representation of direction.
delta(up, 0, -1).
delta(down, 0, 1).
delta(left, -1, 0).
delta(right, 1, 0).

% distance(X,Y,D): Manhattan distance from my player to cell(X,Y).
distance(X,Y,D) :- myPos(MX,MY), cellFree(X,Y), &abs(X-MX;X1), &abs(Y-MY;Y1), D=X1+Y1.

% adjacent(X,Y,X1,Y1,Dir,K): cell(X1,Y1) is adjacent to cell(X,Y) in one direction (considering explosionRange(K)).
adjacent(X,Y,X1,Y1,Dir,K) :-
    cell(X,Y), cell(X1,Y1),
    delta(Dir, DX, DY),
    explosionRange(K),
    X1 = X + DX*K, Y1 = Y + DY*K.

% stealBox(X,Y): position where we can place a bomb to destroy boxes in range that would otherwise
% be destroyed by another player's bomb (strategic bomb placement to steal points).
stealBox(X,Y) :-
    inExplosion(X,Y), haveBomb,
    box(X1,Y1), adjacent(X,Y,X1,Y1,_,1),
    distance(X,Y,D), bomb(_,_,_,T), D < T - 1.

stealBox(X,Y) :-
    inExplosion(X,Y), not haveBomb, myId(ID), ID <> EnemyID,
    box(X1,Y1), adjacent(X,Y,X1,Y1,_,1), adjacent(X,Y,X2,Y2,_,_), not bombAffects(X3,Y3,X1,Y1),
    distance(X,Y,D), bomb(EnemyID,X2,Y2,T), bomb(ID,X3,Y3,T1), D < T - 1, T1 < T - 1.

% tooFarOneBox: true if the player is in a position where the only box in range
% is too far to be efficiently targeted (beyond explosion range 1).
tooFarOneBox :- myPos(X,Y), box(X1,Y1), boxCount(X,Y,1), adjacent(X,Y,X1,Y1,_,R), R > 1.

% myBlownUpBoxes(D): number of boxes destroyed by the player
myBlownUpBoxes(D):- blownUpBoxes(ID,D), myId(ID).

% totalBoxes(T): number of boxes still in game
totalBoxes(T) :- T = #count{X,Y: box(X,Y)}.

% canLose: true if at least one player has more boxes blown up than ours
canLose :- myBlownUpBoxes(D), blownUpBoxes(ID,N), not myId(ID), totalBoxes(T), N + T >= D.

% supremacy: true if the player is blasting opponents
supremacy :- not canLose.
