%  ____                  _                   _ _
% | __ )  ___  _ __ ___ | |__   __ _ _ __ __| (_)_ __   ___
% |  _ \ / _ \| '_ ` _ \| '_ \ / _` | '__/ _` | | '_ \ / _ \
% | |_) | (_) | | | | | | |_) | (_| | | | (_| | | | | | (_) |
% |____/ \___/|_| |_| |_|_.__/ \__,_|_|  \__,_|_|_| |_|\___/

% # Data model, see also the AspAgent class in entities.py
% ## Input
% Initial facts, these do not change
% - cell(X, Y).              <- represents a grid cell
% - myId(ID).                <- the agent's own ID
% - gridSize(Width, Height). <- actual instance is always gridSize(13,11)
% - bombRange(3).            <- bomb explosion propagation range
% Facts modeling the game state at the beginning of the turn
% - box(X, Y).                      <- a box placed on the grid
% - player(ID, X, Y, BombsLeft).    <- BombsLeft is either 0 or 1
% - bomb(OwnerID, X, Y, TurnsLeft). <- TurnsLeft is the detonation timer
% - prevDestination(X, Y).          <- output of the previous turn
% ## Output
% The program produces exactly one of
% - placeBomb(X, Y). <- places a bomb at the current position and
%                       starts moving toward (X, Y) in the same turn
% - move(X, Y).      <- moves one cell closer to (X, Y)


% # Structure of this program
% This program follows the guess-check-optimize paradign. First, all possible
% outcomes are generated (guessed), then outcoms that violate the game
% specification are truncated (check). Finally, the best of the remaining,
% valid, outcomes is choosen via optimization. [1]


maxHittableBoxes(4).  % Max number of boxes that can be blown up with one bomb
bombLifetime(8).  % How many turns a bomb lasts

currentPosition(X, Y) :- myId(Id), player(Id, X, Y, _).

% Between one turn and the next if we are placing a bomb back-to-back BombsLeft
% will remain zero. At the beginning of a turn, if a bomb has a timer value of
% 1 the bomb will explode in this turn and the agent will be able to place the
% bomb again in the same turn. To minimize turns wasted we should aim to do
% exactly that.
hasBomb(Player) :- player(Player, _, _, 1).
hasBomb(Player) :- player(Player, _, _, _), bomb(Player, _, _, 1).


% # GUESS

% 13*11*2 = 286 initial answer sets.
% 143 of type {move(X,Y)} and 143 of type {placeBomb(X,Y)}
{ move(X, Y) : cell(X, Y); placeBomb(X, Y) : cell(X, Y) } = 1.

destination(X, Y) :- move(X, Y).
destination(X, Y) :- placeBomb(X, Y).


% # CHECK

:- move(X, Y), box(X, Y).
:- placeBomb(X, Y), box(X, Y).
:- destination(X, Y), bomb(_, X, Y, _). % It's all going to blow up anyway

destinationReached :- prevDestination(X, Y), currentPosition(X, Y).
bombPlaced :- placeBomb(_, _).

% Place the bomb if and only if we reached our target desination
:- destinationReached, not bombPlaced.
:- not destinationReached, bombPlaced.

% Placing the bomb at the currentPosition would waste a turn
:- prevDestination(X, Y), currentPosition(X, Y), myId(Me), hasBomb(Me),
   placeBomb(X, Y).
:- destinationReached, move(_, _). % Wandering aimlessly is forbidden


% # OPTIMIZE

% cell(Px, Py) and cell(Qx, Qy) are either on the same row or the same column
inLine(Px, Py, Qx, Qy) :- cell(Px, Py), cell(Qx, Qy), Px = Qx.
inLine(Px, Py, Qx, Qy) :- cell(Px, Py), cell(Qx, Qy), Py = Qy.

% Whether a bomb at (Bx, By) will hit the cell at (X, Y)
bombAtCellHitsCell(Bx, By, X, Y) :- cell(Bx, By), cell(X, Y),
                                    inLine(Bx, By, X, Y), bombRange(Range),
                                    &abs(Bx - X; Dx), Dx < Range,
                                    &abs(By - Y; Dy), Dy < Range.
% (Note) All distances computed on the grid are Manhattan distances [2]

% A box at (X, Y) being threatened by a bomb
threatenedBox(X, Y) :- box(X, Y), bomb(_, Bx, By, _),
                       bombAtCellHitsCell(Bx, By, X, Y).

% How many boxes will be hit by a bomb placed at cell(X, Y)
boxesHit(X, Y, N) :- cell(X, Y), not box(X, Y),
                     N = #count { BoxX, BoxY : box(BoxX, BoxY),
                                          bombAtCellHitsCell(X, Y, BoxX, BoxY),
                                          not threatenedBox(BoxX, BoxY) }.

% Maximize number of boxes hit
:~ destination(X, Y), boxesHit(X, Y, N), maxHittableBoxes(Max). [Max - N@2]

% Minimize target cell distance
:~ currentPosition(SrcX, SrcY), destination(DstX, DstY),
   &abs(SrcX - DstX; Dx), &abs(SrcY - DstY; Dy). [Dx + Dy@1]


% If the enemy is closer to our target destination AND it will regain the bomb
% before us, then we could lose the position and have wasted turns to get
% there.
% We exploit the concept of a Voronoi region to discourage such positions
% controlled by the enemy [3].

boxesLeft(Count) :- Count = #count { X, Y : box(X, Y),
                                            not threatenedBox(X, Y) }.

bombCooldown(Player, Cooldown) :- not hasBomb(Player),
                                  bomb(Player, _, _, Cooldown).
bombCooldown(Player, 0) :- player(Player, _, _, _), hasBomb(Player).

:~ destination(X, Y), myId(Me), player(Me, Px, Py, _),
   player(Enemy, Ex, Ey, _), Me != Enemy,
   boxesLeft(BoxesLeft), BoxesLeft > 1,
   &abs(Px - X; DxPlayerDestination), &abs(Py - Y; DyPlayerDestination),
   &abs(Ex - X; DxEnemyDestination), &abs(Ey - Y; DyEnemyDestination),
   MyDistance = DxPlayerDestination + DyPlayerDestination,
   EnemyDistance = DxEnemyDestination + DyEnemyDestination,
   bombCooldown(Me, MyCooldown), bombCooldown(Enemy, EnemyCooldown),
   MyDistance - EnemyDistance + MyCooldown - EnemyCooldown > 1.
   [1@3]


% Box stealing protection. It's relevant only when boxesHit produces 1.
% Stealing happens when we place the bomb at a distance of 2 from the box and
% the enemy places it's bomb between our bomb and the box. This results in us
% getting no points and the enemy getting the one box.
% We check if the target hits only one box and if the enemy could actually
% steal the box, given distance and cooldown. If all conditions are met
% we discourage placing a bomb at a distance of 2.

:~ myId(Me), player(Me, Px, Py, _), player(Enemy, Ex, Ey, _), Me != Enemy,
   box(Bx, By), destination(X, Y), boxesHit(X, Y, 1),
   &abs(Bx - X; DxBombBox), &abs(By - Y; DyBombBox),
   DxBombBox + DyBombBox = 2,

   &abs(Bx - Px; DxAgentBomb), &abs(By - Py; DyAgentBomb),
   &abs(Bx - Ex; DxEnemyBomb), &abs(By - Ey; DyEnemyBomb),
   bombCooldown(Me, MyCooldown), bombCooldown(Enemy, EnemyCooldown),
   &abs(DxAgentBomb + DyAgentBomb - MyCooldown; MyWait),
   &abs(DxEnemyBomb + DyEnemyBomb - EnemyCooldown; EnemyWait),
   bombLifetime(BombLifetime),
   MyWait + BombLifetime > EnemyWait. % Enemy could make it
   [1@2]


% [1]: https://i-dlv.readthedocs.io/en/latest/Basic/basic.html#the-gco
% [2]: https://en.wikipedia.org/wiki/Taxicab_geometry
% [3]: https://en.wikipedia.org/wiki/Voronoi_diagram

