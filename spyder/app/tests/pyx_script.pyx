cpdef int factorial(int x):
    # Basic example of a cython function, which defines
    # python-like operations and control flow on defined c types

    cdef int m = x
    cdef int i

    if x <= 1:
        return 1
    else:
        for i in range(1, x):
            m = m * i
    return m

a = factorial(10)
