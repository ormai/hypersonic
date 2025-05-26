% =========================================
% Author: nASPi Team -> Alessandro Sidero, Lorenzo Giandomenico
% File: naspi_weak_constraints
% Description: Defines weak constraints for optimal answer sets
% (maximize destruction, minimize distance, etc.).
% Requirements:
% - Requires: move/2, boxCount/3, target/2, myPos/2, distance/3, haveBomb/0, placed/0, supremacy/0
% - Depends on: naspi_useful_preds, naspi_cell_score
% =========================================

% Penalize staying on the same position when placing
:~ placed, myPos(X,Y), target(X,Y). [1@10]

% Penalize placing a bomb when we're too far from a single box (wasteful)
:~ placed, tooFarOneBox. [1@9]

% Penalize not placing a bomb when advantageous (no better options)
:~ not supremacy, haveBomb, not placed, myPos(X,Y), boxCount(X,Y,C), C > 0. [C@8,X,Y]

% Penalize not placing a bomb (supremacy mode)
:~ supremacy, haveBomb, not placed, myPos(X,Y), boxCount(X,Y,C), C > 0. [C@8,X,Y]

% Prioritize placing a bomb on a cell where we can steal boxes from opponents
:~ haveBomb, not placed, stealBox(X,Y), myPos(X,Y). [1@7,X,Y]

% Prefer moving to cells where we can steal boxes from opponents
:~ not move(X,Y), stealBox(X,Y), distance(X,Y,D). [D@6,X,Y]

% Avoid placing a bomb if better options with higher box counts are nearby
:~ haveBomb, placed, myPos(X1,Y1), boxCount(X1,Y1,C1),
   cellFree(X2,Y2), boxCount(X2,Y2,C2), distance(X2,Y2,D),
   C2 > C1, D <= 3. [C2-C1@5,X1,Y1,X2,Y2]

% Prefer traveling longer distances for higher box counts when bomb timer allows it
:~ move(X1,Y1), boxCount(X1,Y1,C1), distance(X1,Y1,D1),
   cellFree(X2,Y2), boxCount(X2,Y2,C2), distance(X2,Y2,D2),
   bomb(ID,_,_,T), myId(ID),
   C2 > C1, D2 > D1, D2 < T - 1. [C2-C1@4,X1,Y1,X2,Y2]

% Prefer targeting cells with high boxCount (more destruction)
:~ not supremacy, not move(X,Y), boxCount(X,Y,C), C > 0. [C@3,X,Y]

% Prefer targeting cells with a boxCount of 1 (supremacy mode)
:~ supremacy, not move(X,Y), boxCount(X,Y,C), C > 0. [-C@3,X,Y]

% Penalize moves when we're too far from a single box (wasted movement)
:~ move(X,Y), myPos(X,Y), tooFarOneBox. [1@2,X,Y]

% Prefer actions that minimize travel distance (efficiency)
:~ move(X,Y), distance(X,Y,D). [D@1,X,Y]
