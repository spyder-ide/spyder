ham(N) -> ham(N, 1, 1).

ham(0, F1, _) -> F1;
ham(N, F1, F2) when N > 0 ->
    ham(N - 1, F2, F2 + F1).

Eggs = 10.
Sausage = atom.
HaM = false.
Ham = Eggs + Sausage.