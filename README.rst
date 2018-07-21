Cache Me
========

.. image:: https://img.shields.io/travis/JaredLGillespie/cache.me.svg
    :alt: Travis
    :target: https://travis-ci.org/JaredLGillespie/cache.me
.. image:: https://img.shields.io/coveralls/github/JaredLGillespie/cache.me.svg
    :alt: Coveralls github
    :target: https://coveralls.io/github/JaredLGillespie/cache.me
.. image:: https://img.shields.io/pypi/v/cache.me.svg
    :alt: PyPI
    :target: https://pypi.org/project/cache.me/
.. image:: https://img.shields.io/pypi/wheel/cache.me.svg
    :alt: PyPI - Wheel
    :target: https://pypi.org/project/cache.me/
.. image:: https://img.shields.io/pypi/pyversions/cache.me.svg
    :alt: PyPI - Python Version
    :target: https://pypi.org/project/cache.me/
.. image:: https://img.shields.io/pypi/l/cache.me.svg
    :alt: PyPI - License
    :target: https://pypi.org/project/cache.me/

A library for caching the outputs of functions based on the inputted parameters to reduce recomputing expensive
computations and requesting frequently accessed content, and to improve performance.

.. code-block:: python

    @cache(StaticCache(),
           on_hit=lambda h: print('Hit %s time(s)' % h),
           on_miss=lambda m: print('Missed %s time(s)' % m))
    def fibonacci(n):
        if n < 2:
            return n
        return fib(n-1) + fib(n-2)

Installation
------------

The latest version of cache.me is available via ``pip``:

.. code-block:: python

    pip install cache.me

Alternatively, you can download and install from source:

.. code-block:: python

    python setup.py install

Getting Started
---------------

The ``cache`` decorator contains the following signature:

.. code-block:: python

    @cache(algorithm, include_types=False, on_hit=None, on_miss=None, key_func=None)
    def func(...)
        ...

It serves as both a function decorator, and a runnable wrapper and is configurable through it's dynamic parameters.

In its simplest form, the decorator accepts different algorithms that can be used to cache the outputs of the function
based on its inputs, otherwise known as `memoization`_. Different algorithms are provided to perform this memoization
for different access patterns, as described below.

The creation of the key is based on the arguments and keyword arguments passed in. The type information can also be used
in the formation of the key by setting the ``include_types`` parameter to True. In addition, the arguments used for the
function can be altered before use for the key creation via the ``key_func`` parameter. A common use case for
this is to remove a parameter since as a timer or logging object from the key creation. The function should accept the
same arguments as the calling function and return a tuple of the arguments and keyword arguments to use to create the
key.

.. code-block:: python

    def key_changer(x, logger):
        return (x,), {}

    @cache(RandomCache(size=30), key_func=key_changer)
    def func(x, logger)
        ...

Two callback functions, ``on_hit`` and ``on_miss``, can be passed into the function to be called when either a cache hit
or cache miss occurs. For the most typical use cases, these are passed either the number of hits or number of misses
occurred.

.. _memoization: https://en.wikipedia.org/wiki/Memoization

Bound Function Methods
^^^^^^^^^^^^^^^^^^^^^^

In addition to caching the function, other methods are bound to the function for interacting with the cache. The
following methods are added to the decorated function:

- ``cache_info()``: Returns a tuple of information about the cache containing the number of hits, the number of misses, the current size, and the maximum size.
- ``cache_clear()``: Clears the cache along with its statistics.

.. code-block:: python

    @cache(NMRUCache(30))
    def func(...)
        ...

    # Clear the cache
    func.cache_clear()

    # Grab cache information
    hits, misses, current_size, max_size = func.cache_info()

Caching Algorithms
------------------

The following caching algorithms are provided by the library (although others could be extended from the ``BaseCache``):

- `FIFO (First-in First-out)`_
- `LIFO (Last-in First-out`_
- `LFU (Least Frequently Used)`_
- `LRU (Least Recently Used)`_
- `MQ (Multi-Queue)`_
- MRU (Most Recently Used)
- NMRU (Not Most Recently Used)
- `RR (Random Replacement)`_
- `SLRU (Segmented Least Recently Used)`_
- `Static`
- `TLRU (Time-aware Least Recently Used)`_
- TwoQ (simple 2Q or Two-Queue)
- TwoQFull (full 2Q or Two-Queue)

While each of these can be fed into the ``cache`` decorator, they can also be used on their own by simply creating an
instance and calling the appropriate methods. Each implemented algorithm has an O(1) time complexity for accesses and
insertions, and have the following methods and properties:

- ``current_size``: The current size of the cache.
- ``hits``: The number of cache hits.
- ``max_size``: The maximum size of the cache.
- ``misses``: The number of cache misses.
- ``clear()``: Clears the items in the cache.
- ``get(key, sentinel)``: Gets an item in the cache.
- ``put(key, value)``: Retrieves an item in the cache.
- ``dynamic_methods()``: Provides dynamic binding of methods for ``cache`` decorator.
- ``create_key(...)``: Creates a cache key.

.. _FIFO (First-in First-out): https://en.wikipedia.org/wiki/Cache_replacement_policies#First_in_first_out_(FIFO)
.. _LIFO (Last-in First-out: https://en.wikipedia.org/wiki/Cache_replacement_policies#Last_in_first_out_(LIFO)
.. _LFU (Least Frequently Used): https://en.wikipedia.org/wiki/Cache_replacement_policies#Least-frequently_used_(LFU)
.. _LRU (Least Recently Used): https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)
.. _MQ (Multi-Queue): https://en.wikipedia.org/wiki/Cache_replacement_policies#Multi_queue_(MQ)
.. _MRU (Most Recently Used): https://en.wikipedia.org/wiki/Cache_replacement_policies#Most_recently_used_(MRU)
.. _RR (Random Replacement): https://en.wikipedia.org/wiki/Cache_replacement_policies#Random_replacement_(RR)
.. _SLRU (Segmented Least Recently Used): https://en.wikipedia.org/wiki/Cache_replacement_policies#Segmented_LRU_(SLRU)
.. _TLRU (Time-aware Least Recently Used): https://en.wikipedia.org/wiki/Cache_replacement_policies#Time_aware_least_recently_used_(TLRU)

FIFO (First-in First-out)
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``FIFOCache`` is a First-in First-out cache where keys are evicted in order of arrival when the cache is full.
Accessing a key does not change the order of eviction.

.. code-block:: python

    @cache(FIFOCache(size=50))
    def func(...)
        ...

LIFO (First-in First-out)
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``LIFOCache`` is a Last-in First-out cache where keys are evicted in reverse order of arrival when the cache is
full. Accessing a key does not change the order of eviction.

.. code-block:: python

    @cache(LIFOCache(size=50))
    def func(...)
        ...

LFU (Least Frequently Used)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``LFUCache`` is a Least Frequently Used cache where keys which have been accessed the least number of times are
evicted when the cache is full. The frequency list structure as described in `"An O(1) algorithm for implementing the LFU cache eviction scheme"`_
is implemented.

.. code-block:: python

    @cache(LFUCache(size=50))
    def func(...)
        ...

.. _"An O(1) algorithm for implementing the LFU cache eviction scheme": http://dhruvbird.com/lfu.pdf

LRU (Least Recently Used)
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``LRUCache`` is a Least Recently Used cache where keys which have been accessed the least recently are evicted when
the cache is full.

.. code-block:: python

    @cache(LRUCache(size=50))
    def func(...)
        ...

MFU (Most Frequently Used)
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``MFUCache`` is a Most Frequently Used cache where keys which have been accessed the most number of times are
evicted when the cache is full. This uses the same frequency list structure as described in LFU.

.. code-block:: python

    @cache(MFUCache(size=50))
    def func(...)
        ...

MQ (Multi-Queue)
^^^^^^^^^^^^^^^^

The ``MQCache`` is a Multi-Queue cache in which multiple queues are used to hold levels of varying temperature (i.e.
highly accessed and less accessed) along with a history buffer (similar to 2Q). This is implemented based on the
paper "The Multi-Queue Replacement Algorithm for Second Level Buffer Caches" which uses a LRU queues for each level. The
access count of each item is also recorded and used in determining which queue to promote the item to based on the
``queue_func`` parameter.

Items are also susceptible to being evicted over time. If an item isn't accessed within a certain time it is bumped
down to a lower queue and its expiration time is reset. This continues if the item isn't accessed until it is
eventually evicted to the lowest queue.

The history buffer is a FIFO queue that keeps track of items recently evicted from the queue. If an item is accessed
while in the history buffer, it is placed in the appropriate queue based on it's previous access frequency + 1.

.. code-block:: python

    @cache(MQCache(size=50, buffer_size=10, expire_time=100, num_queues=8,
           queue_func=lambda f: math.log(f, 2), access_based=True))
    def func(...)
        ...

MRU (Most Recently Used)
^^^^^^^^^^^^^^^^^^^^^^^^

The ``MRUCache`` is a Most Recently Used cache where keys which have been accessed the most recently are evicted when
the cache is full.

.. code-block:: python

    @cache(MRUCache(size=50))
    def func(...)
        ...

NMRU (Not Most Recently Used)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``NMRUCache`` is a Not Most Recently Used cache where keys which have not been access the most recently are evicted
when the cache is full. When the cache is full, a random key other than the most recently inserted is removed.

.. code-block:: python

    @cache(NMRUCache(size=50))
    def func(...)
        ...

RR (Random Replacement)
^^^^^^^^^^^^^^^^^^^^^^^

The ``RRCache`` is a Random Replacement cache where keys are evicted randomly, regardless of access of insertion order.

.. code-block:: python

    @cache(RRCache(size=50))
    def func(...)
        ...

SLRU (Segmented Least Recently Used)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``SLRUCache`` is a Segmented Least Recently Used cache which is implemented with two queues, a LRU (the protected),
and a FIFO (the probationary). Items are initially placed into the probationary queue when first placed into the cache.
If this cache is full, items are evicted in the order of their arrival. If items are accessed while they are in the
probationary queue, they are moved to the protected queue. They stay in this queue until it is full and the key
which has been least recently used is moved back to the probationary queue.

Note that this cache implementation is very similar to the simple 2Q algorithm with the exception that items evicted
from the protected cache are moved to the probationary (opposed to being immediately evicted).

.. code-block:: python

    @cache(SLRUCache(protected_size=50, probationary_size=20))
    def func(...)
        ...

Static
^^^^^^

The ``StaticCache`` is a simple cache with no key eviction. Keys are stored permanently, or at least until the cache is
cleared.

.. code-block:: python

    @cache(StaticCache())
    def func(...)
        ...


TLRU (Time-aware Least Recently Used)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``TLRUCache`` is a Time-aware Least Recently-Used cache where keys are prematurely evicted if their last access time
is below a minimum limit, the ``expire_time``. Time in this case is either a simple clock that is incremented each time
the cache is accessed., or the actual time in seconds that has passed. This is determined by the ``access_based``
parameter. If ``reset_on_access`` is True, the ``expire_time`` is reset each time the item is accessed; otherwise it is
expired from the time of initial insertion in the cache.

This is implemented with two LRU lists, one for LRU-based expiration and another for time-based expiration. This is
required due to allowing ``reset_on_access`` to be False, thereby allowing items to be expired independent of how they
are accessed.

.. code-block:: python

    @cache(TLRUCache(expire_time=100, size=50, access_based=False, reset_on_access=True))
    def func(...)
        ...

TwoQ (simple 2Q or Two-Queue)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``TwoQCache`` is the simple 2Q cache described by the algorithm in "2Q: A Low Overhead High Performance Buffer
Management Replacement Algorithm". Two queues are used, an LRU (the primary), and a FIFO (the secondary). Items are
initially placed into the secondary queue when placed into the cache. If the secondary queue is full, items are evicted
in the order of their arrival. If items are accessed while they are in the secondary queue, they are moved to the
primary queue. They stay in this queue until it is full and the key which has been least recently used is evicted.

.. code-block:: python

    @cache(TwoQ(primary_size=50, secondary_size=20))
    def func(...)
        ...

TwoQFull (full 2Q or Two-Queue)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``TwoQFullCache`` is the full 2Q cache as described by the algorithm in "2Q: A Low Overhead High Performance
Buffer Management Replacement Algorithm". Three queues are used, an LRU (the primary), and two FIFO (the secondary
in and out). Items are initially placed into the secondary "in" queue when first placed into the cache. If this queue is
full, items are moved in the order of their arrival into the secondary "out" queue. If items are accessed while they are
in the secondary "in" queue they stay in this queue in their current position.

If items are accessed while they are in the secondary "out" queue they are moved to the primary queue. If this cache
is full, items are evicted in the order of their arrival. Items in the primary queue stay in this queue until it is
full and the key which has been least recently used is evicted. This implementation yields O(1) access and insertion
time.

.. code-block:: python

    @cache(TwoQFull(primary_size=50, secondary_in_size=20, secondary_out_size=20))
    def func(...)
        ...

Advanced Usage
--------------

Instead of using as a decorator, ``cache`` can be used as an instead for wrapping an arbitrary number of function calls.
This can be achieved via the ``run`` method.

.. code-block:: python

    def func_a():
        ...

    def func_b():
        ...

    cacher = cache(algorithm=...)

    # Using same configured cache instance
    cache.run(func_a, args, kwargs)
    cache.run(func_b, args, kwargs)

Besides using the provided ``run`` method, like any decorator functions can be locally wrapped, passed around, and
executed.

.. code-block:: python

    def func():
        ...

    cacher = cache(algorithm=...)
    cache_func = cacher(func)
    cache_func(args, kwargs)

    # Or as a one-off like so
    cache(...)(func)(args, kwargs)

Both the ``on_hit`` and ``on_miss`` callback functions that can be passed into ``cache`` can actually be configured to
accepts different number of parameters depending on the function. They can each either accept 0 parameters, the
parameters that would be typically passed in, or the wrapped function's args and kwargs in addition to the parameters
typically given.

Optionally passing in the args and kwargs allows for building more complex callback functions. Each of the possible
function variations are shown below.

.. code-block:: python

    def on_hit(): ...
    def on_hit(error): ...
    def on_hit(error, *args, **kwargs): ...

    def on_miss(): ...
    def on_miss(value): ...
    def on_miss(value, *args, **kwargs): ...

In addition to the ``cache_info()`` and ``cache_clear()`` methods bound to the function, others can be dynamically bound
to the function depending on the algorithm. None of the current basic implementations use this functionality, but this
has a case for when creating one's own or extending the existing algorithms. The dynamic methods are prefixed with
'cache_'.

.. code-block:: python

    import copy

    class FancyCache(LRUCache):
        def __init__(self, size):
            super(size).__init__()

        def show_all(self):
            # Retrieve a copy of the current items in the cache
            return copy(self._map)

        def dynamic_methods(self):
            return ['show_all']

    @cache(FancyCache())
    def func(x, y)
        ...

    func(1, 2)
    func(3, 4)

    # Dynamic methods are prefixed with 'cache_'
    items = func.cache_show_all()

Contribution
------------

Contributions or suggestions are welcome! Feel free to `open an issue`_ if a bug is found or an enhancement is desired,
or even a `pull request`_.

.. _open an issue: https://github.com/JaredLGillespie/cache.me/issues
.. _pull request: https://github.com/JaredLGillespie/cache.me/compare

Changelog
---------

All changes and versioning information can be found in the `CHANGELOG`_.

.. _CHANGELOG: https://github.com/JaredLGillespie/cache.me/blob/master/CHANGELOG.rst

License
-------

Copyright (c) 2018 Jared Gillespie. See `LICENSE`_ for details.

.. _LICENSE: https://github.com/JaredLGillespie/cache.me/blob/master/LICENSE.txt
