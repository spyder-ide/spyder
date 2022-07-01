# Module example in Elixir

defmodule Example do
  use GenServer

  def fact(0, accum) do
    accum
  end

  def fact(n, accum \\ 1) do
    fact(n - 1, accum * n)
  end
end
