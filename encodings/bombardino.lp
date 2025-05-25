% Bombardino — A Bomberman agent


% Group: GameStopppers (the third p is absolutely intentional and not a typo)
% - Mario G. D'Andrea, 245940
% - Orlando Sgrò, 240594


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
% - score(ID, Score).               <- currenct score for each player
% ## Output
% The program produces exactly one of
% - placeBomb(X, Y). <- places a bomb at the current position and
%                       starts moving toward (X, Y) in the same turn
% - move(X, Y).      <- moves one cell closer to (X, Y)


% /~~~~~~~~~~~~ Structure of this program ~~~~~~~~~~~~\
% This program follows the guess-check-optimize paradign. First, all possible
% outcomes are generated (guessed); then outcomes that violate the game
% specification are pruned (check). Finally, the best of the remaining — valid
% — outcomes is choosen through optimization. [1]


% /~~~~~~~~~~~~ THE PLAN ~~~~~~~~~~~~\
% We search for the max number of boxes we can hit with one bomb.
% Then we "rank" them based on the distance from our position.
% In a perfect world this would be the end but the are in a competitive
% environment, so we need to keep an eye on position where the enemy could
% arrive before us.
% Also since we have an enemy we can try to get some points by stealing boxes
% from the enemy.
% Stealing also resets our bomb cooldown, so we can take advantage of their
% reset to palce more bombs.
% But since the enemy could also setal from us we need to try and protect
% ourself, at lest in the end-game were few point could make the difference.


% /~~~~~~~~~~~~ FACTS ~~~~~~~~~~~~\
% A few initial facts that are useful to our agent
maxHittableBoxes(4). % Max number of boxes that can be blown up with one bomb
bombLifetime(8). % How many turns a bomb lasts
currentPosition(X, Y) :- myId(Id), player(Id, X, Y, _).

% Between one turn and the next, if we are placing a bomb back-to-back
% BombsLeft will remain zero. At the beginning of a turn, if a bomb has a timer
% value of 1 it will explode in this turn and the agent will be able to place
% the bomb again in the same turn. To minimize turns wasted we should aim
% to do exactly that.
hasBomb(Player) :- player(Player, _, _, 1).
hasBomb(Player) :- player(Player, _, _, _), bomb(Player, _, _, 1).

enemy(Id) :- myId(Me), player(Id, _, _, _), Me != Id.


% /~~~~~~~~~~~~ GUESS ~~~~~~~~~~~~\
% 13*11*2 = 286 initial answer sets.
% 143 of type {move(X,Y)} and 143 of type {placeBomb(X,Y)}
{ move(X, Y) : cell(X, Y); placeBomb(X, Y) : cell(X, Y) } = 1.
destination(X, Y) :- move(X, Y).
destination(X, Y) :- placeBomb(X, Y).


% /~~~~~~~~~~~~ CHECK ~~~~~~~~~~~~\
:- move(X, Y), box(X, Y).
:- placeBomb(X, Y), box(X, Y).
:- destination(X, Y), bomb(_, X, Y, _). % It's all going to blow up anyway

% Place the bomb if and only if we reached our target desination
destinationReached :- prevDestination(X, Y), currentPosition(X, Y).
bombPlaced :- placeBomb(_, _).

% We do not want to place bomb in the wrong posisition or risk moving wrongly
:- destinationReached, not bombPlaced.
:- not destinationReached, bombPlaced.

% Placing the bomb at the currentPosition would waste a turn
:- prevDestination(X, Y), currentPosition(X, Y), myId(Me), hasBomb(Me),
   placeBomb(X, Y).
:- destinationReached, move(_, _). % Wandering aimlessly is forbidden

% Forbid wasting even more turns.
:- currentPosition(X, Y), boxesHit(X, Y, 0), move(X, Y).


% /~~~~~~~~~~~~ OPTIMIZE ~~~~~~~~~~~~\

% # Weights:
% 5 steal enemy box
% 4 avoid cells of distance 2 from a box if the enemy can steal it
% 3 avoid positions controlled by the enemy
% 2 maximize boxes hit with one bomb
% 1 minimize target distance

% cell(Px, Py) and cell(Qx, Qy) are either on the same row or the same column
inLine(Px, Py, Qx, Qy) :- cell(Px, Py), cell(Qx, Qy), Px = Qx.
inLine(Px, Py, Qx, Qy) :- cell(Px, Py), cell(Qx, Qy), Py = Qy.

% Whether a bomb at (Bx, By) will hit the cell at (X, Y)
% (Note) All distances computed on the grid are Manhattan distances [2]
bombAtCellHitsCell(Bx, By, X, Y) :- cell(Bx, By), cell(X, Y),
                                    inLine(Bx, By, X, Y), bombRange(Range),
                                    &abs(Bx - X; Dx), Dx < Range,
                                    &abs(By - Y; Dy), Dy < Range.

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

% (Note) The following rules are big, the possibility of factorizing out common
%        literals into their own rules was considered but dismissed. This way
%        we minimize the overall number of rule instantiations.

% If the enemy is closer to our target destination AND it will regain the bomb
% before us, then we could lose the position and have wasted turns to get
% there.
% We exploit the concept of a Voronoi region to discourage choosing such
% positions controlled by the enemy [3].
bombCooldown(Player, Cooldown) :- not hasBomb(Player),
                                  bomb(Player, _, _, Cooldown).
bombCooldown(Player, 0) :- player(Player, _, _, _), hasBomb(Player).

:~ destination(X, Y), myId(Me), player(Me, Px, Py, _),
   enemy(Enemy), player(Enemy, Ex, Ey, _),

   &abs(Px - X; DxPlayerDestination),
   &abs(Py - Y; DyPlayerDestination),
   MyDistance = DxPlayerDestination + DyPlayerDestination,

   &abs(Ex - X; DxEnemyDestination),
   &abs(Ey - Y; DyEnemyDestination),
   EnemyDistance = DxEnemyDestination + DyEnemyDestination,

   bombCooldown(Me, MyCooldown), bombCooldown(Enemy, EnemyCooldown),
   MyDistance - EnemyDistance + MyCooldown - EnemyCooldown > 1.
   [1@3]

% Penalize in the same way all remaining positions that offer no points.
% Without this, in cases where all positions that hit a bomb are
% controlled by the enemy, we would be left with random cells.
% And from some testing the cells is basically always the one we're on.
:~ destination(X, Y), boxesHit(X, Y, 0). [1@3]

% Box stealing protection. It's relevant only when boxesHit produces 1.
% Stealing happens when we place the bomb at a distance of 2 from the box and
% the enemy places its bomb between our bomb and the box. This results in us
% getting no points and the enemy getting the one box and a fast reset.
% We check if the target hits only one box and if the enemy could actually
% steal the box, given distance and cooldown. If all conditions are met
% we discourage placing a bomb at a distance of 2.
:~ destination(X, Y), boxesHit(X, Y, 1),
   box(Bx, By),
   &abs(Bx - X; DxBombBox),
   &abs(By - Y; DyBombBox),
   DxBombBox + DyBombBox = 2,

   % We compare our wait plus the time that the bomb takes to explode
   % the time the enemy would require to place the bomb that would steal our
   % box. Each wait is the max between the bomb cooldown and the distance
   %              max(a, b) = floor((a + b + abs(a - b)) / 2)
   currentPosition(Px, Py),
   &abs(Bx - Px; DxAgentBomb),
   &abs(By - Py; DyAgentBomb),
   MyDistance = DxAgentBomb + DyAgentBomb,
   myId(Me), bombCooldown(Me, MyCooldown),
   &abs(MyDistance - MyCooldown; MyDiff),
   MyWait = (MyDistance + MyCooldown + MyDiff) / 2,

   enemy(Enemy), player(Enemy, Ex, Ey, _),
   &abs(Bx - Ex; DxEnemyBomb),
   &abs(By - Ey; DyEnemyBomb),
   EnemyDistance = DxEnemyBomb + DyEnemyBomb,
   bombCooldown(Enemy, EnemyCooldown),
   &abs(EnemyDistance - EnemyCooldown; EnemyDiff),
   EnemyWait = (EnemyDistance + EnemyCooldown + EnemyDiff) / 2,

   bombLifetime(BombLifetime),
   MyWait + BombLifetime >= EnemyWait. % Enemy could make it
   [1@4]

% Box stealing takes a point that would otherwise go to the enemy and gives it
% to us and it gives us a fast reset of the bomb.
% Assigning the highest priority to stealing might not be always the best
% choice, but it is possible only under very specific conditions, so we can
% afford to give it the highest priority.
% If the conditions were too loose we could result in an agent that only steals
% and that is most likely not the best strategy...
steal(X, Y) :- mmyId(Me), enemy(Eney), bomb(Enemy, BombX, BombY, Timer),
               box(BoxX, BoxY), inLine(BombX, BombY, BoxX, BoxY),
               &abs(BombX - BoxX; DxBombBox),
               &abs(BombY - BoxY; DyBombBox),
               DxBombBox + DyBombBox = 2, % There's space for our bomb
               X = (BombX + BoxX) / 2, Y = (BombY + BoxY) / 2, % midpoint

               % We can reach it bofere the enemy bomb explodes
               currentPosition(Px, Py), &abs(Px - X; Dx), &abs(Py - Y; Dy),
               Dx + Dy < Timer - 1,

               % We will have the bomb before the enemy bomb explodes
               bombCooldown(Me, Cooldown),
               Cooldown < Timer - 1.

:~ steal(X, Y), currentPosition(X, Y), not bombPlaced. [1@5]
:~ steal(X, Y), currentPosition(Px, Py), Px != X, not move(X, Y). [1@5]
:~ steal(X, Y), currentPosition(Px, Py), Py != Y, not move(X, Y). [1@5]


% [1]: https://i-dlv.readthedocs.io/en/latest/Basic/basic.html#the-gco
% [2]: https://en.wikipedia.org/wiki/Taxicab_geometry
% [3]: https://en.wikipedia.org/wiki/Voronoi_diagram


% /~~~~~~~~~~~~ Notes and fun facts ~~~~~~~~~~~~\
% - The name `Bombardino` comes from the italian version of Brawl Stars'
%   eponymous character.
% - prevDestination is used only to avoid wasting turns.
% - Each row is no longer than 80 characters.
% - The program is long because I like ruels to use more rows instead of being
%   compact for me at least it helps it's readability.
