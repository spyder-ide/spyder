# %% pre
    @typing.overload
    def __init__(
        self: AsyncDispatcher[collections.abc.Awaitable[_T]],
        *,
        loop: LoopID | None = ...,
        early_return: typing.Literal[False] = ...,
        return_awaitable: typing.Literal[True] = ...,
    ) -> None: ...

# %% sig
    def __init__(
        self,
        *,
        loop: LoopID | None = None,
        early_return: bool = True,
        return_awaitable: bool = False,
    ) -> None:
# %% doc
        """
        Decorate a coroutine to run in a specific event loop.

        The ``loop`` parameter can be an existing
        :class:`asyncio.AbstractEventLoop` or a
        :class:`~collections.abc.Hashable` to identify an existing or new one
        created by the :class:`!AsyncDispatcher`. If the loop is not running,
        it will be started in a new thread and managed by the
        :class:`!AsyncDispatcher`.

        This instance can be called with the same arguments as the coroutine it
        wraps and will return a :class:`concurrent.futures.Future` object,
        or an awaitable :class:`asyncio.Future` for the current running event
        loop or the result of the coroutine depending on the ``early_return``
        and ``return_awaitable`` parameters.

        Parameters
        ----------
        loop : LoopID | None, optional
            The event loop to be used, by default the current event loop.
        early_return : bool, optional
            Return the coroutine as a :class:`concurrent.futures.Future`
            before it is done. ``True`` by default.
        return_awaitable : bool, optional
            Return the coroutine as an awaitable :class:`asyncio.Future`
            instead of a :class:`concurrent.futures.Future`, independent of
            the value of ``early_return``. ``False`` by default.


        Examples
        --------

        Non-blocking usage (returns a :class:`concurrent.futures.Future`):

        .. code-block:: python

            @AsyncDispatcher()
            async def my_coroutine(...):
                ...

            future = my_coroutine(...)  # Non-blocking call

            result = future.result()  # Blocking call


        Blocking usage (returns the result):

        .. code-block:: python

            @AsyncDispatcher(early_return=False)
            async def my_coroutine(...):
                ...

            result = my_coroutine(...)  # Blocking call

        Coroutine usage (returns an awaitable :class:`asyncio.Future`):

        .. code-block:: python

            @AsyncDispatcher(return_awaitable=True)
            async def my_coroutine(...):
                ...

            result = await my_coroutine(...)  # Wait for the result to be ready
        """
# %% body
        self._loop = self.get_event_loop(loop)
        self._early_return = early_return
        self._return_awaitable = return_awaitable
# %% post

    @typing.overload
    def __call__(
        self: AsyncDispatcher[collections.abc.Awaitable[_T]],
        async_func: collections.abc.Callable[
            _P, collections.abc.Awaitable[_T]
        ],
    ) -> collections.abc.Callable[_P, collections.abc.Awaitable[_T]]: ...

# %% numpy
        """
        Decorate a coroutine to run in a specific event loop.

        The ``loop`` parameter can be an existing
        :class:`asyncio.AbstractEventLoop` or a
        :class:`~collections.abc.Hashable` to identify an existing or new one
        created by the :class:`!AsyncDispatcher`. If the loop is not running,
        it will be started in a new thread and managed by the
        :class:`!AsyncDispatcher`.

        This instance can be called with the same arguments as the coroutine it
        wraps and will return a :class:`concurrent.futures.Future` object,
        or an awaitable :class:`asyncio.Future` for the current running event
        loop or the result of the coroutine depending on the ``early_return``
        and ``return_awaitable`` parameters.

        Parameters
        ----------
        loop : LoopID | None, optional
            The event loop to be used, by default the current event loop.
        early_return : bool, optional
            Return the coroutine as a :class:`concurrent.futures.Future`
            before it is done. ``True`` by default.
        return_awaitable : bool, optional
            Return the coroutine as an awaitable :class:`asyncio.Future`
            instead of a :class:`concurrent.futures.Future`, independent of
            the value of ``early_return``. ``False`` by default.

        Returns
        -------
        None

        Examples
        --------

        Non-blocking usage (returns a :class:`concurrent.futures.Future`):

        .. code-block:: python

            @AsyncDispatcher()
            async def my_coroutine(...):
                ...

            future = my_coroutine(...)  # Non-blocking call

            result = future.result()  # Blocking call


        Blocking usage (returns the result):

        .. code-block:: python

            @AsyncDispatcher(early_return=False)
            async def my_coroutine(...):
                ...

            result = my_coroutine(...)  # Blocking call

        Coroutine usage (returns an awaitable :class:`asyncio.Future`):

        .. code-block:: python

            @AsyncDispatcher(return_awaitable=True)
            async def my_coroutine(...):
                ...

            result = await my_coroutine(...)  # Wait for the result to be ready
        """
# %% google
        """
        Decorate a coroutine to run in a specific event loop.

        The ``loop`` parameter can be an existing
        :class:`asyncio.AbstractEventLoop` or a
        :class:`~collections.abc.Hashable` to identify an existing or new one
        created by the :class:`!AsyncDispatcher`. If the loop is not running,
        it will be started in a new thread and managed by the
        :class:`!AsyncDispatcher`.

        This instance can be called with the same arguments as the coroutine it
        wraps and will return a :class:`concurrent.futures.Future` object,
        or an awaitable :class:`asyncio.Future` for the current running event
        loop or the result of the coroutine depending on the ``early_return``
        and ``return_awaitable`` parameters.

        Parameters
        ----------
        loop : LoopID | None, optional
            The event loop to be used, by default the current event loop.
        early_return : bool, optional
            Return the coroutine as a :class:`concurrent.futures.Future`
            before it is done. ``True`` by default.
        return_awaitable : bool, optional
            Return the coroutine as an awaitable :class:`asyncio.Future`
            instead of a :class:`concurrent.futures.Future`, independent of
            the value of ``early_return``. ``False`` by default.

        Returns
        -------
        None

        Examples
        --------

        Non-blocking usage (returns a :class:`concurrent.futures.Future`):

        .. code-block:: python

            @AsyncDispatcher()
            async def my_coroutine(...):
                ...

            future = my_coroutine(...)  # Non-blocking call

            result = future.result()  # Blocking call


        Blocking usage (returns the result):

        .. code-block:: python

            @AsyncDispatcher(early_return=False)
            async def my_coroutine(...):
                ...

            result = my_coroutine(...)  # Blocking call

        Coroutine usage (returns an awaitable :class:`asyncio.Future`):

        .. code-block:: python

            @AsyncDispatcher(return_awaitable=True)
            async def my_coroutine(...):
                ...

            result = await my_coroutine(...)  # Wait for the result to be ready
        """
# %% sphinx
        """
        Decorate a coroutine to run in a specific event loop.

        The ``loop`` parameter can be an existing
        :class:`asyncio.AbstractEventLoop` or a
        :class:`~collections.abc.Hashable` to identify an existing or new one
        created by the :class:`!AsyncDispatcher`. If the loop is not running,
        it will be started in a new thread and managed by the
        :class:`!AsyncDispatcher`.

        This instance can be called with the same arguments as the coroutine it
        wraps and will return a :class:`concurrent.futures.Future` object,
        or an awaitable :class:`asyncio.Future` for the current running event
        loop or the result of the coroutine depending on the ``early_return``
        and ``return_awaitable`` parameters.

        Parameters
        ----------
        loop : LoopID | None, optional
            The event loop to be used, by default the current event loop.
        early_return : bool, optional
            Return the coroutine as a :class:`concurrent.futures.Future`
            before it is done. ``True`` by default.
        return_awaitable : bool, optional
            Return the coroutine as an awaitable :class:`asyncio.Future`
            instead of a :class:`concurrent.futures.Future`, independent of
            the value of ``early_return``. ``False`` by default.

        Returns
        -------
        None

        Examples
        --------

        Non-blocking usage (returns a :class:`concurrent.futures.Future`):

        .. code-block:: python

            @AsyncDispatcher()
            async def my_coroutine(...):
                ...

            future = my_coroutine(...)  # Non-blocking call

            result = future.result()  # Blocking call


        Blocking usage (returns the result):

        .. code-block:: python

            @AsyncDispatcher(early_return=False)
            async def my_coroutine(...):
                ...

            result = my_coroutine(...)  # Blocking call

        Coroutine usage (returns an awaitable :class:`asyncio.Future`):

        .. code-block:: python

            @AsyncDispatcher(return_awaitable=True)
            async def my_coroutine(...):
                ...

            result = await my_coroutine(...)  # Wait for the result to be ready
        """