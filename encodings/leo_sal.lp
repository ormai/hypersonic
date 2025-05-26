% COSTANTI
iD(ID):- player(ID,_,_,_).  % Ricavo gli ID
bombTime(8).                % tempo di esplosione delle bombe
accuracy(100).              % utilizzato per valutare con maggior precisione il valore delle celle
length(50).                 % distanza di esplorazione della mappa, per valutare la distanza
% explosionRange
explosionRange(1).          % range di esplosione delle bombe
explosionRange(R):- explosionRange(A), bombRange(B), R = A+1, R < B.
bombPlace(X,Y):- bomb(_,X,Y,_).     % coordinate X,Y delle bombe



% Quali solo le casse che possono esser prese per player?
% actual box ci dice quali box non hanno bombe vicino
actualBox(ID,X,Y):- iD(ID), iD(ID2), ID!=ID2, box(X,Y), not collectedBox(ID,X,Y), not collectedBox(ID2,X,Y). % box senza bombe vicine, calcolo del valore delle celle vicine

% Salviamo quali casse e in quale turno verrano prese per giocatore
collectedBoxTime(ID,X,Y1,T):- bomb(ID,X,Y,T), explosionRange(R), box(X,Y1), Y1 = Y - R, not box(X,Y2), Y2=Y1+1.
collectedBoxTime(ID,X1,Y,T):- bomb(ID,X,Y,T), explosionRange(R), box(X1,Y), X1 = X + R, not box(X2,Y), X2=X1-1.
collectedBoxTime(ID,X,Y1,T):- bomb(ID,X,Y,T), explosionRange(R), box(X,Y1), Y1 = Y + R, not box(X,Y2), Y2=Y1-1.
collectedBoxTime(ID,X1,Y,T):- bomb(ID,X,Y,T), explosionRange(R), box(X1,Y), X1 = X - R, not box(X2,Y), X2=X1+1.
collectedBox(ID,X,Y):- collectedBoxTime(ID,X,Y,T). % Join delle precedenti

% Individuo le box collezionabili per cella a seconda del player
adjacent(ID,X,Y,X,Y1):- cell(X,Y), explosionRange(R), actualBox(ID,X,Y1), Y1 = Y - R, not actualBox(ID,X,Y2), Y2=Y1+1.
adjacent(ID,X,Y,X1,Y):- cell(X,Y), explosionRange(R), actualBox(ID,X1,Y), X1 = X + R, not actualBox(ID,X2,Y), X2=X1-1.
adjacent(ID,X,Y,X,Y1):- cell(X,Y), explosionRange(R), actualBox(ID,X,Y1), Y1 = Y + R, not actualBox(ID,X,Y2), Y2=Y1-1.
adjacent(ID,X,Y,X1,Y):- cell(X,Y), explosionRange(R), actualBox(ID,X1,Y), X1 = X - R, not actualBox(ID,X2,Y), X2=X1+1.
% Per ogni celle sommiamo quante celle sono raggiungibili piazzandovi una bomba
cellValue(ID,X,Y,V):- iD(ID), not bombPlace(X,Y), not box(X,Y) ,cell(X,Y), V1=#count{X1,Y1:adjacent(ID,X,Y,X1,Y1)}, V=V1*10.

% celle che sono raggiunte da un'esplosione e quindi esploderanno prima
% inoltre ogni player ha le proprie cellBomb, esse non coincidono.
cellBomb(ID,X,Y,Ti) :- iD(ID), iD(ID2), ID2!=ID, cell(X,Y), not box(X,Y), explosionRange(R), bomb(ID2,X,Y1,Ti), Y1 = Y - R, not box(X,Y2), Y2=Y1+1.
cellBomb(ID,X,Y,Ti) :- iD(ID), iD(ID2), ID2!=ID, cell(X,Y), not box(X,Y), explosionRange(R), bomb(ID2,X,Y1,Ti), Y1 = Y + R, not box(X,Y2), Y2=Y1-1.
cellBomb(ID,X,Y,Ti) :- iD(ID), iD(ID2), ID2!=ID, cell(X,Y), not box(X,Y), explosionRange(R), bomb(ID2,X1,Y,Ti), X1 = X + R, not box(X2,Y), X2=X1-1.
cellBomb(ID,X,Y,Ti) :- iD(ID), iD(ID2), ID2!=ID, cell(X,Y), not box(X,Y), explosionRange(R), bomb(ID2,X1,Y,Ti), X1 = X - R, not box(X2,Y), X2=X1+1.

% Conto quante box ha adianceti una cellBomb
cellBombAdj(ID,X,Y,X,Y1,Ti) :- cellBomb(ID,X,Y,Ti), explosionRange(R), box(X,Y1), not collectedBox(ID,X,Y1), Y1 = Y - R, not box(X,Y2), Y2=Y1+1.
cellBombAdj(ID,X,Y,X,Y1,Ti) :- cellBomb(ID,X,Y,Ti), explosionRange(R), box(X,Y1), not collectedBox(ID,X,Y1), Y1 = Y + R, not box(X,Y2), Y2=Y1-1.
cellBombAdj(ID,X,Y,X1,Y,Ti) :- cellBomb(ID,X,Y,Ti), explosionRange(R), box(X1,Y), not collectedBox(ID,X1,Y), X1 = X + R, not box(X2,Y), X2=X1-1.
cellBombAdj(ID,X,Y,X1,Y,Ti) :- cellBomb(ID,X,Y,Ti), explosionRange(R), box(X1,Y), not collectedBox(ID,X1,Y), X1 = X - R, not box(X2,Y), X2=X1+1.
% Somma dei valori precendi per cella, ci salviamo anche il tempo di esplosione
cellBombValue(ID,X,Y,V,Ti) :- cellBomb(ID,X,Y,Ti), V1=#count{X1,Y1 : cellBombAdj(ID,X,Y,X1,Y1,_)}, V=V1*10, V!=0.


% ESPLORAZIONE
% mi segno le celle attualmente bloccate per attribuire un valore di timelock
uncollected(X,Y):- box(X,Y), iD(ID1), iD(ID2), not collectedBox(ID1,X,Y), not collectedBox(ID2,X,Y), ID1!=ID2.
blocked(X,Y):- collectedBoxTime(_,X,Y,_).
blocked(X,Y):- bomb(_,X,Y,_).
blocked(X,Y):- uncollected(X,Y).
lock(X,Y,0):- cell(X,Y), not blocked(X,Y). % Le celle non bloccate hanno lock=0
lock(X,Y,T):- cell(X,Y), blocked(X,Y), bomb(_,X,Y,T). % bloccata finchè non esplode
lock(X,Y,T):- cell(X,Y), blocked(X,Y), collectedBoxTime(_,X,Y,T). % bloccata finchè non verrà collezionata
lock(X,Y,L+2):- cell(X,Y), uncollected(X,Y), length(L).    % Sempre bloccata

dist(ID,X,Y,0):- player(ID,X,Y,_).  % distanza iniziale zero.
% Movimenti possibili per cella
choice(X,Y,X,Y+1) :- cell(X,Y), cell(X,Y+1).
choice(X,Y,X,Y-1) :- cell(X,Y), cell(X,Y-1).
choice(X,Y,X+1,Y) :- cell(X,Y), cell(X+1,Y).
choice(X,Y,X-1,Y) :- cell(X,Y), cell(X-1,Y).
% fase esplorativa, inizio a simulare il movimento all'interno della griglia di gioco
dist(ID,X1,Y1,D+1) :- dist(ID,X,Y,D), choice(X,Y,X1,Y1), lock(X1,Y1,T), D+1>=T, D < L, length(L).
% ricavo la distanza minima da ogni cella per ogni player
minDist(ID,X,Y,D):- iD(ID), cellValue(ID,X,Y,_), #min{D1: dist(ID,X,Y,D1)}=D.       % prendo la distanza minima per le cellValue
minDist(ID,X,Y,D):- iD(ID), cellBombValue(ID,X,Y,_,_), #min{D1: dist(ID,X,Y,D1)}=D. % prendo la distanza minima per le cellBomb

% Distanza in relazione alla bomba carica
% Se riesco a raggiungere una cella prima che abbia la bomba carica, il tragitto ha costo zero
% Se risco a raggiungerla parzialmente con la bomba in ricarica il costo del tragitto è la differenza tra le due
% Se la bomba è carica il costo è uguale alla distanza del tragitto
actualDist(ID,X,Y,D):- minDist(ID,X,Y,D1), bomb(ID,X1,Y1,Ti), D=0, D1<=Ti.
actualDist(ID,X,Y,D):- minDist(ID,X,Y,D1), bomb(ID,X1,Y1,Ti), D=D1-Ti, D1>Ti.
actualDist(ID,X,Y,D):- minDist(ID,X,Y,D), player(ID,X1,Y1,1).

% Quali celle che vengono triggerate da una bomba posso raggiungere?
% Mi assicuro di arrivare in tempo in una cellBomb e di avere la bomba pronta da piazzare
% Se la mia è carica allora controllo solo di poterla raggiungere
% in ogni caso il tempo di esplosione della triggeredCell è pari alla differenza tra la distanza e il suo tempo di esplosione
triggeredCell(ID,X,Y,V,D1,BT):-  cellBombValue(ID,X,Y,V,T), minDist(ID,X,Y,D), D<T-1, BT=T-D, bomb(ID,_,_,Ti), Ti<=D, actualDist(ID,X,Y,D1).
triggeredCell(ID,X,Y,V,D1,BT):-  cellBombValue(ID,X,Y,V,T), minDist(ID,X,Y,D), D<T-1, BT=T-D, player(ID,_,_,1), actualDist(ID,X,Y,D1).

% per tutte le cellValue il tempo di esplosione della bomba è pari a 8
cellValueCost(ID,X,Y,V,D,BT):- cellValue(ID,X,Y,V), actualDist(ID,X,Y,D), bombTime(BT).
checkOneBox(1) :- #max{V:cellValueCost(_,_,_,V,_,_)}=10.
%cellValueCost(ID,X,Y,V,D,BT):- triggeredCell(ID,X,Y,V,D,BT).

% Calcoliamo il valore delle celle in relazione alla loro distanza e al tempo di esplosione della bomba.
% inoltre decremento il valore delle celle che sono più lontane da me rispetto all'avversario.
% Vengono decrementate in proporzione
%   -----------
% le triggered cell, sono solitamente delle soluzione sub ottime, preferiamo utilizzare il tempo a nostro favore rispetto all'avversario
% per raggiungere delle celle con un maggior numero di box vicine
score(ID,X,Y,S):- cellValueCost(ID,X,Y,V,D,BT), myId(ID), iD(ID2), ID!=ID2, actualDist(ID,X,Y,D1), actualDist(ID2,X,Y,D0), D1<=D0, accuracy(K), S=V*K/(D+BT).
score(ID,X,Y,S):- cellValueCost(ID,X,Y,V,D,BT), myId(ID), iD(ID2), ID!=ID2, actualDist(ID,X,Y,D1), actualDist(ID2,X,Y,D0), D1>D0, Dt=(D1-D0),  accuracy(K), S=(((V*D0)/D1)*K)/(D+BT).
score(ID,X,Y,S):- triggeredCell(ID,X,Y,V,D,BT), accuracy(K), S=((V*2)/3)*K/(D+BT).

% ---------------------------------

score(ID,X,Y,S):-checkOneBox(C), C=1, adjacent(ID,X,Y,X1,Y1), &abs(X-X1;X2), &abs(Y-Y1;Y2), Z=X2+Y2, Z=1, cellValueCost(ID,X,Y,V,D,BT), myId(ID), iD(ID2), ID!=ID2, actualDist(ID,X,Y,D1), actualDist(ID2,X,Y,D0), D1>D0, Dt=(D1-D0), accuracy(K), S=(((V*D0)/D1)*K*K)/(D+BT).
score(ID,X,Y,S):-checkOneBox(C), C=1, adjacent(ID,X,Y,X1,Y1), &abs(X-X1;X2), &abs(Y-Y1;Y2), Z=X2+Y2, Z=1, cellValueCost(ID,X,Y,V,D,BT), myId(ID), iD(ID2), ID!=ID2, actualDist(ID,X,Y,D1), actualDist(ID2,X,Y,D0), D1<=D0, accuracy(K), S=V*K*K/(D+BT).
score(ID,X,Y,S):- triggeredCell(ID,X,Y,V,D,BT), cellBombAdj(ID,X,Y,X1,Y1,Ti), accuracy(K), &abs(X-X1;X2), &abs(Y-Y1;Y2),Z=X2+Y2, Z=1, S=((V*K*K*2)/3)*K/(D+BT),  checkOneBox(C), C=1.

% -----------------------------

% Tra tutte le score prendo quelle con il valore maggiore
bestScore(ID,X,Y,Max):- score(ID,X,Y,Max),  #max{ S: score(ID,X1,Y1,S)}=Max.

% Scelgo una tra queste e vedo quale ha la distanza minima dalla seconda migliore
inBest(ID,X,Y,V) | outBest(ID,X,Y,V):- myId(ID), bestScore(ID,X,Y,V).
:- #count{X,Y : inBest(_,X,Y,_)}!=1.

% Simulo di aver messo la bomba in inBest e tolgo dall'insieme delle adjacent quelle che raggiungo
collectedBox2(ID,X,Y):- collectedBox(ID,X,Y).
collectedBox2(ID,X1,Y1):- inBest(ID,X,Y), adjacent(ID,X,Y,X1,Y1).
removeAdj(X1,Y1):- inBest(ID,X,Y,_), adjacent(ID,X,Y,X1,Y1).
adjacent2(ID,X,Y,X1,Y1):- adjacent(ID,X,Y,X1,Y1), not removeAdj(X1,Y1).
cellValue2(ID,X,Y,V):- iD(ID), not bombPlace(X,Y), not box(X,Y) ,cell(X,Y), V1=#count{X1,Y1:adjacent2(ID,X,Y,X1,Y1)}, V=V1*10, V!=0.

% identifico la prossima mossa migliore
secondBest(ID,X,Y,Max):- cellValue2(ID,X,Y,Max), #max{V: cellValue2(_,_,_,V)}=Max.
% Identifico la distanza minima dalla prossima cella migliore
minDistSecond(ID,X,Y,D):- inBest(ID,X,Y,_), secondBest(ID,X1,Y1,V1), &abs(X-X1;X2), &abs(Y-Y1;Y2), D = X2+Y2.
minimum(Min):- Min=#min{M:minDistSecond(_,_,_,M)}.
:~ minimum(Min). [Min@1]
:~ checkOneBox(C), C=1, inBest(ID,X,Y,V), adjacent(ID,X,Y,X1,Y1), &abs(X-X1;X2), &abs(Y-Y1;Y2), K=X2+Y2. [K@2]



check(ID):- secondBest(ID,_,_,_).

placeBomb(X1,Y1):- myId(ID), inBest(ID,X,Y,_), secondBest(ID,X1,Y1,_), player(ID,X,Y,1).
move(X,Y):- myId(ID), inBest(ID,X,Y,_), not placeBomb(X1,Y1), secondBest(ID,X1,Y1,_).

placeBomb(X,Y):- myId(ID), inBest(ID,X,Y,_), player(ID,X,Y,1), not check(ID).
move(X,Y):- myId(ID), inBest(ID,X,Y,_), not check(ID), not placeBomb(X,Y).
