# %% pre
    @typing.overload
    def __call__(
        self: AsyncDispatcher[_T],
        async_func: collections.abc.Callable[
            _P, collections.abc.Awaitable[_T]
        ],
    ) -> collections.abc.Callable[_P, _T]: ...

# %% sig
    def __call__(
        self: AsyncDispatcher[collections.abc.Awaitable[_T]],
        /,
        async_func: collections.abc.Callable[
            _P,
            collections.abc.Awaitable[_T],
        ],
        *,
        kwonly_param: "StringAnnotation | None" = StringAnnotation(
            "val1",
            "val2",
        ),
        str_param = "spam",
        **kwargs,
    ) -> collections.abc.Callable[
        _P,
        _T | DispatcherFuture[_T] | collections.abc.Awaitable[_T],
    ]:
# %% doc
        """
        Run the coroutine in the event loop.
        """
# %% body
        if not asyncio.iscoroutinefunction(async_func):
            msg = f"{async_func} is not a coroutine function"
            raise TypeError(msg)

        @functools.wraps(async_func)
        def wrapper(
            *args: _P.args,
            **kwargs: _P.kwargs,
        ) -> _T | DispatcherFuture[_T] | collections.abc.Awaitable[_T]:
            task = run_coroutine_threadsafe(
                async_func(*args, **kwargs),
                loop=self._loop,
            )
            if self._return_awaitable:
                return asyncio.wrap_future(
                    task,
                    loop=asyncio.get_running_loop(),
                )

            if self._early_return:
                AsyncDispatcher._running_tasks.append(task)
                task.add_done_callback(self._callback_task_done)
                return task
            return task.result()

        return wrapper
# %% post

    @staticmethod
    def _callback_task_done(future: Future):
        AsyncDispatcher._running_tasks.remove(future)

    @classmethod
    def get_event_loop(
        cls,
        loop_id: LoopID | None = None,
    ) -> asyncio.AbstractEventLoop:
        """Get the event loop to run the coroutine."""
# %% numpy
        """
        Run the coroutine in the event loop.

        Parameters
        ----------
        async_func : collections.abc.Callable[_P, collections.abc.Awaitable[_T]]
            DESCRIPTION.
        kwonly_param : StringAnnotation | None, optional
            DESCRIPTION. The default is StringAnnotation("val1", "val2").
        str_param : TYPE, optional
            DESCRIPTION. The default is "spam".
        **kwargs : TYPE
            DESCRIPTION.

        Returns
        -------
        collections.abc.Callable[_P, _T | DispatcherFuture[_T] | collections.abc.Awaitable[_T]]
            DESCRIPTION.

        Raises
        ------
        TypeError
            DESCRIPTION.
        """
# %% google
        """Run the coroutine in the event loop.

        Args:
            async_func (collections.abc.Callable[_P, collections.abc.Awaitable[_T]]): DESCRIPTION.
            kwonly_param (StringAnnotation | None, optional): DESCRIPTION. Defaults to StringAnnotation("val1", "val2").
            str_param (TYPE, optional): DESCRIPTION. Defaults to "spam".
            **kwargs (TYPE): DESCRIPTION.

        Returns:
            collections.abc.Callable[_P, _T | DispatcherFuture[_T] | collections.abc.Awaitable[_T]]: DESCRIPTION.

        Raises:
            TypeError: DESCRIPTION.
        """
# %% sphinx
        """Run the coroutine in the event loop.

        :param async_func: DESCRIPTION
        :type async_func: collections.abc.Callable[_P, collections.abc.Awaitable[_T]]
        :param kwonly_param: DESCRIPTION, defaults to StringAnnotation("val1", "val2")
        :type kwonly_param: StringAnnotation | None
        :param str_param: DESCRIPTION, defaults to "spam"
        :type str_param: TYPE
        :param **kwargs: DESCRIPTION
        :type **kwargs: TYPE

        :rtype: collections.abc.Callable[_P, _T | DispatcherFuture[_T] | collections.abc.Awaitable[_T]]
        :returns: DESCRIPTION

        :raises TypeError: DESCRIPTION
        """
