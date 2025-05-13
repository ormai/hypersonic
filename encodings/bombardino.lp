%  ____                  _                   _ _
% | __ )  ___  _ __ ___ | |__   __ _ _ __ __| (_)_ __   ___
% |  _ \ / _ \| '_ ` _ \| '_ \ / _` | '__/ _` | | '_ \ / _ \
% | |_) | (_) | | | | | | |_) | (_| | | | (_| | | | | | (_) |
% |____/ \___/|_| |_| |_|_.__/ \__,_|_|  \__,_|_|_| |_|\___/

% ## Input data model
% Initial facts, these do not change
% - cell(X, Y).              <- represents a grid cell
% - myId(ID).                <- the agent's own ID
% - gridSize(Width, Height).
% - bombRange(3).            <- bomb explosion propagation range
% Facts modeling the game state at the beginning of the turn
% - box(X, Y).                      <- a box placed on the grid
% - player(ID, X, Y, BombsLeft).    <- BombsLeft is either 0 or 1
% - bomb(OwnerID, X, Y, TurnsLeft). <- TurnsLeft is the detonation timer
% - prevDestination(X, Y).          <- output of the previous turn

% ## Output data model
% The program produces on of
% - placeBomb(X, Y). <- places a bomb at the current position and
%                       starts moving toward (X, Y) in the same turn
% - move(X, Y).      <- moves one cell closer to (X, Y)

% Known facts
maxHittableBoxes(4). % one for each direction
bombLifetime(8). % turns

% Basic knowledge
currentPosition(X, Y) :- myId(Id), player(Id, X, Y, _).

% Between one turn and the next if we are placing
% a bomb back to back BombsLeft will always be zero.
haveBomb :- myId(Id), player(Id, _, _, 1).
haveBomb :- myId(Id), bomb(Id, _, _, 1).


% # GUESS

% 13 * 11 * 2 = 286 initial answer sets
{ move(X, Y) : cell(X, Y); placeBomb(X, Y) : cell(X, Y) } = 1.

destination(X, Y) :- move(X, Y).
destination(X, Y) :- placeBomb(X, Y).


% # CHECK

:- move(X, Y), box(X, Y).
:- placeBomb(X, Y), box(X, Y).
:- destination(X, Y), bomb(_, X, Y, _). % it's all going to blow up anyway

% cell(Px, Py) and cell(Qx, Qy) are either on the same row or the same column
inLine(Px, Py, Qx, Qy) :- cell(Px, Py), cell(Qx, Qy), Px = Qx.
inLine(Px, Py, Qx, Qy) :- cell(Px, Py), cell(Qx, Qy), Py = Qy.

% Whether a bomb at (Bx, By) will hit the cell at (X, Y)
bombAtCellHitsCell(Bx, By, X, Y) :- cell(Bx, By), cell(X, Y),
                                    inLine(Bx, By, X, Y), bombRange(Range),
                                    &abs(Bx - X; Dx), Dx < Range,
                                    &abs(By - Y; Dy), Dy < Range.

% A box at (X, Y) being threatened by a bomb
threatenedBox(X, Y) :- box(X, Y), bomb(_, Bx, By, _),
                       bombAtCellHitsCell(Bx, By, X, Y).

% how many boxes will be hit by a bomb placed at cell(X, Y)
boxesHit(X, Y, N) :- cell(X, Y), not box(X, Y),
                     N = #count { BoxX, BoxY : box(BoxX, BoxY),
                                          bombAtCellHitsCell(X, Y, BoxX, BoxY),
                                          not threatenedBox(BoxX, BoxY) }.


destinationReached :- prevDestination(X, Y), currentPosition(X, Y).
bombPlaced :- placeBomb(_, _).

% Place the bomb if and only if we reached the optimum desination
:- destinationReached, not bombPlaced.
:- not destinationReached, bombPlaced.

% Placing the bomb at the currentPosition would waste a turn
:- prevDestination(X, Y), currentPosition(X, Y), haveBomb, placeBomb(X, Y).
:- destinationReached, move(_, _).


% # OPTIMIZE

% Maximize number of boxes hit
:~ destination(X, Y), boxesHit(X, Y, N), maxHittableBoxes(Max). [Max - N@2]

% Manhattan distance is used
:~ currentPosition(SrcX, SrcY), destination(DstX, DstY),
   &abs(SrcX - DstX; Dx), &abs(SrcY - DstY; Dy). [Dx + Dy@1]

% Guess:
% creare un answer set per ogni possibile mossa, ognuno del tipo {move(X, Y)} o {placeBomb(X, Y)}
%
% Check:
% escludere gli answer set invalidi tramite strong constraint, tipo andare in
% una cella in cui c'è una cassa.
% Le box già minacciate da una bomba sono escluse tramite uno strong constraint.
%
% Optimize:
% Obiettivo grezzo: fare più punti possibili percorrendo la minore distanza possibile.
%
% Decidere di muoversi verso una cella ottima distante più di 8 celle quando si
% ha una cella subottima più vicina è da scoraggiare.

% Documentazione utile: https://i-dlv.readthedocs.io/en/latest/
