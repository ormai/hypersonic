% =========================================
% Author: nASPi Team -> Alessandro Sidero, Lorenzo Giandomenico
% File: naspi_explosion_logic
% Description: Handles the modeling of explosion propagation and obstruction.
% Identifies which cells are affected by bombs, directly or indirectly.
% Requirements:
% - Facts: bombPos/2, box/2
% - Support from: naspi_useful_preds for adjacent/4, cellFree/2
% =========================================

% inExplosion(X,Y): cell(X,Y) will be affected by an explosion.
inExplosion(X,Y) :- bombPos(X,Y).

inExplosion(X1,Y1) :-
    bombPos(X,Y),
    adjacent(X,Y,X1,Y1,Dir,K),
    not blockedExplosion(X1,Y1,Dir,K).

% blockedExplosion(X,Y,Dir,K): explosion from (X,Y) is blocked by a box or a bomb.
blockedExplosion(X,Y,Dir,K) :-
    cellFree(X,Y),
    J<K, J>0, explosionRange(K),
    adjacent(Xb,Yb,X,Y,Dir,J),
    box(Xb,Yb).

blockedExplosion(X,Y,Dir,K) :-
    cellFree(X,Y),
    J<K, J>0, explosionRange(K),
    adjacent(Xb,Yb,X,Y,Dir,J),
    bombPos(Xb,Yb).

% bombAffects(X,Y,X1,Y1): a bomb at (X,Y) can affect a box at (X1,Y1).
bombAffects(X,Y,X1,Y1) :- cell(X,Y), box(X1,Y1), adjacent(X,Y,X1,Y1,_,_).
