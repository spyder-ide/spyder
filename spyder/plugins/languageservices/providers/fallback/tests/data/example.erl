
%% Some comment in Erlang

-module(example).
-export[fib/1, some_function/0, this_function/0].

fib(N) -> fib(N, 0, 1).

fib(N, F1, F2) -> fib(N - 1, F2, F1 + F2);
fib(0, _, F2) -> F2.

some_function() -> {ok, "textString"}.

this_function() ->
    {ok, Variable} = some_function(),
    case Variable of
        2 -> error;
        _ -> ok
    end.

spawn_process() ->
    Pid = spawn(example, fib, [8]),
    {msg, self()} ! Pid.
