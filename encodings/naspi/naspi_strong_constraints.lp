% =========================================
% Author: nASPi Team -> Alessandro Sidero, Lorenzo Giandomenico
% File: naspi_strong_constraints
% Description: Strong constraints that invalidate illegal actions.
% Requirements:
% - Requires: haveBomb/0
% - Depends on: naspi_useful_preds
% =========================================

% Cannot place a bomb if my player don't have any.
:- placeBomb(X,Y), not haveBomb.
