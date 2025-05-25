% =========================================
% Author: nASPi Team -> Alessandro Sidero, Lorenzo Giandomenico
% File: naspi_cell_score
% Description: Assigns a score to cells based on how many boxes a bomb would destroy.
% Requirements:
% - Requires: bombAffects/4, cellFree/2
% - Assumes: inExplosion/2 is available to avoid counting affected boxes
% =========================================

% hits(X,Y,X1,Y1): a bomb at (X,Y) would hit a box at (X1,Y1) if box at (X1,Y1) is not already in explosion.
hits(X,Y,X1,Y1) :- bombAffects(X,Y,X1,Y1), not inExplosion(X1,Y1).

% boxCount(X,Y,C): C is the number of boxes that would be destroyed from (X,Y).
boxCount(X,Y,C) :- cellFree(X,Y), C = #count { X1,Y1 : hits(X,Y,X1,Y1) }.
