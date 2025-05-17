%  ____                  _                   _ _
% | __ )  ___  _ __ ___ | |__   __ _ _ __ __| (_)_ __   ___
% |  _ \ / _ \| '_ ` _ \| '_ \ / _` | '__/ _` | | '_ \ / _ \
% | |_) | (_) | | | | | | |_) | (_| | | | (_| | | | | | (_) |
% |____/ \___/|_| |_| |_|_.__/ \__,_|_|  \__,_|_|_| |_|\___/

% # Data model, see also the AspAgent class in entities.py
%
% ## Input
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
%
% ## Output
% The program produces exactly one of
% - placeBomb(X, Y). <- places a bomb at the current position and
%                       starts moving toward (X, Y) in the same turn
% - move(X, Y).      <- moves one cell closer to (X, Y)


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

% 13 * 11 * 2 = 286 initial answer sets
{ move(X, Y) : cell(X, Y); placeBomb(X, Y) : cell(X, Y) } = 1.

destination(X, Y) :- move(X, Y).
destination(X, Y) :- placeBomb(X, Y).


% # CHECK

:- move(X, Y), box(X, Y).
:- placeBomb(X, Y), box(X, Y).
:- destination(X, Y), bomb(_, X, Y, _). % It's all going to blow up anyway

destinationReached :- prevDestination(X, Y), currentPosition(X, Y).
bombPlaced :- placeBomb(_, _).

% Place the bomb if and only if we reached the optimum desination
:- destinationReached, not bombPlaced.
:- not destinationReached, bombPlaced.

% Placing the bomb at the currentPosition would waste a turn
:- prevDestination(X, Y), currentPosition(X, Y), myId(Me), hasBomb(Me), placeBomb(X, Y).
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

% A box at (X, Y) being threatened by a bomb
threatenedBox(X, Y) :- box(X, Y), bomb(_, Bx, By, _),
                       bombAtCellHitsCell(Bx, By, X, Y).

% how many boxes will be hit by a bomb placed at cell(X, Y)
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
% before us, then we could lose the position and have wasted turns to get there.
% We exploit the concept of a Voronoi region to discourage such positions
% controlled by the enemy [2].

bombCooldown(Player, Cooldown) :- not hasBomb(Player),
                                  bomb(Player, _, _, Cooldown).
bombCooldown(Player, 0) :- player(Player, _, _, _), hasBomb(Player).

:~ destination(X, Y), myId(Me), player(Me, Px, Py, _),
   player(Enemy, Ex, Ey, _), Me != Enemy,
   &abs(Px - X; DxPlayerDestination), &abs(Py - Y; DyPlayerDestination),
   &abs(Ex - X; DxEnemyDestination), &abs(Ey - Y; DyEnemyDestination),
   MyDistance = DxPlayerDestination + DyPlayerDestination,
   EnemyDistance = DxEnemyDestination + DyEnemyDestination,
   bombCooldown(Me, MyCooldown), bombCooldown(Enemy, EnemyCooldown),
   MyDistance - EnemyDistance + MyCooldown - EnemyCooldown > 1.
   [1@3]

% se c'è rischio di bomb stealing la bomba va piazzata a ridosso della cassa

%:- id(Id), player(Id, Px, Py, _), &abs(Bx - Px; DxAgentBomb), &abs(By - Py; DyAgentBomb),
%   player(Enemy, Ex, Ey, _), &abs(Bx - Ex; DxEnemyBomb), &abs(By - Ey; DyEnemyBomb),
%   bombLifetime(BombLifetime),
%   DxAgentBomb + DyAgentBomb + BombLifetime <= DxEnemyBomb + DyEnemyBomb,
%   destination(X, Y), boxesHit(X, Y, 1),
%   box(Bx, By), &abs(Bx - X; DxBombBox), &abs(By - Y; DyBombBox),
%   DxBombBox + DyBombBox = 2.
% se la distanza tra me e la cassa + bombLifetime è minore della distanza del nemico dalla bomba

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

% [1]: https://en.wikipedia.org/wiki/Taxicab_geometry
% [2]: https://en.wikipedia.org/wiki/Voronoi_diagram
