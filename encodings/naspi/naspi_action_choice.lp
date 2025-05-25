% =========================================
% Author: nASPi Team -> Alessandro Sidero, Lorenzo Giandomenico
% File: naspi_action_choice
% Description: Models decision making by selecting a movement or a bomb placement action.
% Requirements:
% - Requires: cellFree/2 from naspi_useful_preds
% - Assumes: strong constraints and scoring are handled elsewhere
% =========================================

% target(X,Y): chosen target cell to move to.
{ target(X,Y) : cellFree(X,Y) } = 1.

% move(X,Y): movement action to cell (X,Y).
% placeBomb(X,Y): bomb placement and then move to cell (X,Y).
placeBomb(X,Y) | move(X,Y) :- target(X,Y).
