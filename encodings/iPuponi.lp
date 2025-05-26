%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% DEFINIZIONI INIZIALI
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

{posRand(X, Y)} = 1 :- cell(X,Y).

% Offset relativi per il controllo delle adiacenze (entro 2 celle in ogni direzione)
offset(1, 0). offset(2, 0). offset(-1, 0). offset(-2, 0).
offset(0, 1). offset(0, 2). offset(0, -1). offset(0, -2).



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% CONTEGGIO E VERIFICA ADIACENZE
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Conta il numero di box adiacenti alla cella candidata (posRand)
adjacentBoxCount(X, Y, N) :-
    posRand(X, Y),
    N = #count {
        X2, Y2 : offset(DX, DY), X2 = X + DX, Y2 = Y + DY, box(X2, Y2)
    }.

% Una cella (X, Y) è adiacente a una box se almeno una box si trova nelle vicinanze
adjacentToBox(X, Y) :-
    offset(DX, DY),
    X2 = X + DX, Y2 = Y + DY,
    box(X2, Y2).

% Trova il numero massimo di box adiacenti tra tutte le celle
maxAdjacent(N) :-
    N = #max { B : posRand(X, Y), adjacentBoxCount(X, Y, B) }.

% Solo le celle col numero massimo di box adiacenti sono valide per piazzare la bomba
canPlaceBomb(X, Y) :-
    posRand(X, Y),
    adjacentBoxCount(X, Y, N),
    maxAdjacent(N).



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% AZIONI CONSENTITE
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Il giocatore può decidere se muoversi o piazzare una bomba nella posizione scelta
move(X, Y) | placeBomb(X, Y) :-
    posRand(X, Y),
    player(ID, _, _, _),
    myId(ID),
    canPlaceBomb(X, Y).



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% VINCOLI
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Non puoi piazzare una bomba se non ne possiedi
:- placeBomb(_, _), player(ID, _, _, 0), myId(ID).

% Non puoi piazzare una bomba se non sei adiacente a una box
:- placeBomb(_, _), player(ID, PX, PY, 1), myId(ID), not adjacentToBox(PX, PY).



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% FUNZIONE OBIETTIVO (OTTIMIZZAZIONE)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% PRIORITÀ: se ho una bomba e sono vicino a 4 box, piazzare è molto buono (meno penalità)
:~ placeBomb(X, Y), player(ID, _, _, 1), myId(ID), adjacentBoxCount(X, Y, N). [-N@1, X, Y]

% Se ho una bomba, preferisco piazzarla piuttosto che muovermi (muoversi è penalizzato)
:~ move(X, Y), player(ID, _, _, 1), myId(ID), adjacentBoxCount(X, Y, N). [-N@2, X, Y]

% Se NON ho bombe, devo muovermi. Preferisco andare dove ci sono più box
:~ move(X, Y), player(ID, _, _, 0), myId(ID), adjacentBoxCount(X, Y, N). [-N@3, X, Y]



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% VINCOLI AVANZATI (SELEZIONE MIGLIORE)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Esiste almeno una cella con 2 o più box adiacenti
existsBetter :- posRand(X, Y), adjacentBoxCount(X, Y, N), N >= 2.

% Vincolo: non piazzare la bomba se la cella scelta ha solo 1 cassa adiacente e ci sono alternative migliori
:- placeBomb(X, Y), player(ID, PX, PY, 1), myId(ID), adjacentBoxCount(PX, PY, 1), existsBetter.
