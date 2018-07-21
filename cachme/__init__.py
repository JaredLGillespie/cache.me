# MIT License
#
# Copyright (c) 2018 Jared Gillespie
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""A library for caching the outputs of functions based on the inputted parameters to reduce recomputing expensive
computations and requesting frequently accessed content, and to improve performance.

This exports:
  - cache is the function decorator
  - BaseCache is an abstract class other caching classes derive from
  - FIFOCache is a First-in First-out cache
  - LFUCache is a Least Frequently Used cache
  - LRUCache is a Least Recently Used cache
  - MFUCache is a Most Frequently Used cache
  - MQCache is an implementation of the Multi-Queue cache
  - MRUCache is a Most Recently Used cache
  - NMRUCache is a Not Most Recently Used cache
  - RRCache is a Random Replacement cache
  - SLRUCache is a Segmented Least Recently Used cache
  - StaticCache is a simple cache with no key eviction
  - TLRUCache is a Time-aware Least Recently Used cache
  - TwoQCache is an implementation of the simple 2Q algorithm
  - TwoQFullCache is an implementation of the full 2Q algorithm
"""


__all__ = ['cache', 'BaseCache', 'FIFOCache', 'LFUCache', 'LRUCache', 'MFUCache', 'MQCache', 'MRUCache', 'NMRUCache',
           'RRCache', 'SLRUCache', 'StaticCache', 'TLRUCache', 'TwoQCache', 'TwoQFullCache']


from abc import ABC, abstractmethod
from collections import namedtuple, deque
from inspect import signature, Parameter
from functools import wraps
from threading import RLock
from time import time
import math


_CacheInfo = namedtuple('CacheInfo', ['hits', 'misses', 'current_size', 'max_size'])


class _FunctionSignature:
    """Flags for parameters accepted by function signature."""
    NORMAL = 1 << 0
    ARGS = 1 << 1
    KWARGS = 1 << 2


class cache:
    """Function caching decorator.

    Wraps a function and caches successive calls with the same given parameters and optional typing information.

    Different caching algorithms can be utilized, those of which extend the provided `BaseCache` class. Each
    implementation is thread-safe and all current implementations are O(1) for insertions and accesses.

    The cache can be cleared via the `cache_clear` function and caching information can be retrieved from the function
    by calling `cache_info`. The following properties are returned in a namedtuple `CacheInfo`:
     - hits: number of cache hits
     - misses: number of cache misses
     - current_size: current size of the cache
     - max_size: maximum size of the cache

    Other methods from the caching algorithm can be dynamically appended to the wrapped function and will use the
    `cache_<method name>` naming convention.

    Callback functions can be provided for cache hits and misses, `on_hit` and `on_miss` respectively. They can either
    accept 0 parameters, the number of parameters as described below, or the wrapped function's args and kwargs in
    addition to the parameters as described below.

    For usage examples, see https://github.com/JaredLGillespie/cache.me.

    :param algorithm:
        A caching algorithm that should inherit from `BaseCache`. Provides the actual caching implementation while
        leaving the decorating behavior to this `cache` decorator.
    :param include_types:
        Whether to include typing information for the keys. If True, values that would otherwise hash similarly will
        create different keys (i.e. integer 0 and float 0.0 are different). Defaults to False.
    :param on_hit:
        A callable function to be called when a cache hit occurs. A cache hit occurs when an entry is found in the cache
        The function should accept a single value, the number of cache hits.
    :param on_miss:
        A callable function to be called when a cache miss occurs. A cache miss occurs when an entry isn't found in the
        cache. The function should accept a single value, the number of cache misses.
    :param key_func:
        A callable function to manipulate the arguments and keyword arguments being used to create the cache key. Should
        accept the same arguments and parameters as the calling function and return a tuple of the arguments and keyword
        arguments to use to create the cache key.
    :type algorithm: BaseCache
    :type include_types: bool
    :type on_hit: callable
    :type on_miss: callable
    :type key_func: callable
    """
    def __init__(self, algorithm, include_types=False, on_hit=None, on_miss=None, key_func=None):
        self.algorithm = algorithm
        self.include_types = include_types
        self.on_hit = on_hit
        self.on_miss = on_miss
        self.key_func = key_func

        # Dynamic methods
        for method in algorithm.dynamic_methods:
            setattr(self, 'cache_' + method, getattr(algorithm, method))

        # Signatures
        self._sig_hit = None if not callable(on_hit) else self._define_function_signature(on_hit)
        self._sig_miss = None if not callable(on_miss) else self._define_function_signature(on_miss)

    def __call__(self, func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            return self.run(func, *args, **kwargs)

        func_wrapper.cache_info = self.cache_info
        func_wrapper.cache_clear = self.cache_clear

        # Dynamic methods prefixed with `cache_`
        for method in self.algorithm.dynamic_methods:
            setattr(func_wrapper, 'cache_' + method, getattr(self.algorithm, method))

        return func_wrapper

    def run(self, func, *args, **kwargs):
        """Executes a function using this as the wrapper.

        :param func:
            A function to wrap and call.
        :param args:
            Arguments to pass to the function.
        :param kwargs:
            Keyword arguments to pass to the function.
        :type func: function
        """
        sentinel = object()
        key_args, key_kwargs = args, kwargs

        if self.key_func:
            key_args, key_kwargs = self.key_func(*args, **kwargs)

        key = self.algorithm.create_key(key_args, key_kwargs, self.include_types)

        ret = self.algorithm.get(sentinel, key)

        if ret != sentinel:
            if self.on_hit is not None:
                self._call_with_sig(self.on_hit, self._sig_hit, (self.algorithm.hits,), *args, **kwargs)
            return ret

        if self.on_miss is not None:
            self._call_with_sig(self.on_miss, self._sig_miss, (self.algorithm.misses,), *args, **kwargs)

        ret = func(*args, **kwargs)

        self.algorithm.put(key, ret)

        return ret

    def cache_info(self):
        """Report cache statistics."""
        return _CacheInfo(self.algorithm.hits, self.algorithm.misses, self.algorithm.current_size, self.algorithm.max_size)

    def cache_clear(self):
        """Clear the cache and cache statistics."""
        self.algorithm.clear()

    def _call_with_sig(self, func, sig, internal_args, *args, **kwargs):
        if not sig:
            return func()
        elif sig & (_FunctionSignature.ARGS | _FunctionSignature.KWARGS):
            return func(*(internal_args + args), **kwargs)
        else:
            return func(*internal_args)

    def _define_function_signature(self, func):
        sig = None

        for param in signature(func).parameters.values():
            if param.kind == Parameter.POSITIONAL_OR_KEYWORD:
                sig = (sig or _FunctionSignature.NORMAL) | _FunctionSignature.NORMAL
            elif param.kind == Parameter.VAR_KEYWORD:
                sig = (sig or _FunctionSignature.KWARGS) | _FunctionSignature.KWARGS
            elif param.kind == Parameter.VAR_POSITIONAL:
                sig = (sig or _FunctionSignature.ARGS) | _FunctionSignature.ARGS

        return sig


# Nodes
class _Node:
    __slots__ = ['prev', 'next']

    def __init__(self):
        self.prev = None
        self.next = None


class _KeyNode(_Node):
    __slots__ = ['key']

    def __init__(self, key):
        super().__init__()
        self.key = key


class _FrequencyNode(_Node):
    __slots__ = ['frequency', 'keys']

    def __init__(self, frequency):
        super().__init__()
        self.frequency = frequency
        self.keys = set()


class _ExpiryNode(_Node):
    __slots__ = ['key', 'expire_time']

    def __init__(self, key, expire_time):
        super().__init__()
        self.key = key
        self.expire_time = expire_time


# Data containers
class _NodeData:
    __slots__ = ['value', 'node']

    def __init__(self, value, node):
        self.value = value
        self.node = node


class _FrequencyData:
    __slots__ = ['value', 'frequency_node']

    def __init__(self, value, frequency_node):
        self.value = value
        self.frequency_node = frequency_node


class _ExpiryData:
    __slots__ = ['value', 'queue_node', 'access_queue_node']

    def __init__(self, value, queue_node, access_queue_node):
        self.value = value
        self.queue_node = queue_node
        self.access_queue_node = access_queue_node


class _KeyValue:
    __slots__ = ['key', 'value']

    def __init__(self, key, value):
        self.key = key
        self.value = value


class _MQData:
    __slots__ = ['value', 'frequency', 'node']

    def __init__(self, value, frequency, node):
        self.value = value
        self.frequency = frequency
        self.node = node


# Data structures
class _LinkedList:
    __slots__ = ['node_cls', 'head', 'tail', 'size']

    def __init__(self, node_cls):
        self.node_cls = node_cls
        self.head = None
        self.tail = None
        self.size = 0

    def __len__(self):
        return self.size

    def access(self, node):
        if node != self.head:
            if node == self.tail:
                self.tail = node.prev
            else:
                node.next.prev = node.prev

            node.prev.next = node.next
            node.prev = None
            node.next = self.head
            self.head.prev = node
            self.head = node

    def append(self, *args):
        self.size += 1

        node = self.node_cls(*args)
        if self.head is None:
            self.head = node
            self.tail = node
        else:
            node.next = self.head
            node.next.prev = node
            self.head = node
        return node

    def clear(self):
        self.head = None
        self.tail = None
        self.size = 0

    def peek(self):
        return None if self.tail is None else self.tail

    def pop(self):
        self.size -= 1

        if self.head == self.tail:
            node = self.head
            self.head = None
            self.tail = None

            node.next = None
            node.prev = None
            return node

        node = self.tail
        self.tail = node.prev
        self.tail.next = None

        node.next = None
        node.prev = None
        return node

    def pop_left(self):
        self.size -= 1

        if self.head == self.tail:
            node = self.tail
            self.head = None
            self.tail = None

            node.next = None
            node.prev = None
            return node

        node = self.head
        self.head = node.next
        self.head.prev = None

        node.next = None
        node.prev = None
        return node

    def remove(self, node):
        self.size -= 1

        if node.prev is not None:
            node.prev.next = node.next

        if node.next is not None:
            node.next.prev = node.prev

        if node == self.head:
            self.head = node.next

        if node == self.tail:
            self.tail = node.prev

        node.next = None
        node.prev = None


class _FreqList:
    __slots__ = ['node_cls', 'head', 'tail', 'size']

    def __init__(self, node_cls):
        self.node_cls = node_cls
        self.head = None
        self.tail = None
        self.size = 0

    def __len__(self):
        return self.size

    def access(self, node, key):
        if len(node.keys) == 1:
            # Move to the next node if key + 1
            if node.next is not None and node.next.frequency == node.frequency + 1:
                node.next.prev = node.prev

                if node.prev:
                    node.prev.next = node.next

                node.next.keys.add(key)

                if self.head == node:
                    self.head = node.next

                return node.next
            else:  # Otherwise increment entire node
                node.frequency += 1
                return node
        else:
            node.keys.remove(key)
            # Move to the next node if key + 1
            if node.next is not None and node.next.frequency == node.frequency + 1:
                node.next.keys.add(key)
                return node.next
            else:  # Otherwise create a new node
                new_node = self.node_cls(node.frequency + 1)
                new_node.keys.add(key)
                new_node.prev = node
                new_node.next = node.next
                new_node.prev.next = new_node

                if new_node.next:
                    new_node.next.prev = new_node

                if self.tail == node:
                    self.tail = new_node

                return new_node

    def append(self, key):
        self.size += 1

        if self.head is None:
            node = self.node_cls(1)
            node.keys.add(key)
            self.head = node
            self.tail = node
            return node
        elif self.head.frequency == 1:
            self.head.keys.add(key)
            return self.head
        else:
            node = self.node_cls(1)
            node.keys.add(key)
            node.next = self.head
            self.head.prev = node
            self.head = node
            return node

    def clear(self):
        self.head = None
        self.tail = None
        self.size = 0

    def pop(self):
        self.size -= 1
        key = self.tail.keys.pop()

        if len(self.tail.keys) == 0:
            if self.head == self.tail:
                self.head = None
                self.tail = None
            else:
                self.tail.prev.next = None
                self.tail = self.tail.prev

        return key

    def pop_left(self):
        self.size -= 1
        key = self.head.keys.pop()

        if len(self.head.keys) == 0:
            if self.head == self.tail:
                self.head = None
                self.tail = None
            else:
                self.head.next.prev = None
                self.head = self.head.next

        return key


class _HashList(list):
    """Proxy list for ensuring hash() is called no more than once.

    Borrowed from `functools`: https://docs.python.org/3/library/functools.html
    """
    __slots__ = ['_hash']

    def __init__(self, tup):
        super().__init__(tup)
        self._hash = hash(tup)

    def __hash__(self):
        return self._hash


# Caching algorithms
class BaseCache(ABC):
    """Cache interface in which other caching algorithms should implement."""
    def __init__(self):
        super().__init__()

    @property
    @abstractmethod
    def current_size(self):
        """Returns the current size of the cache.

        :return:
            The current size of the cache.
        :rtype: int
        """

    @property
    @abstractmethod
    def hits(self):
        """Returns the number of cache hits.

        :return:
            The number of cache hits.
        :rtype: int
        """

    @property
    @abstractmethod
    def max_size(self):
        """Returns the maximum size of the cache.

        :return:
            The maximum size of the cache.
        :rtype: int
        """

    @property
    @abstractmethod
    def misses(self):
        """Returns the number of cache misses.

        :return:
            The number of cache misses.
        :rtype: int
        """

    @abstractmethod
    def clear(self):
        """Clears the items in the cache."""

    @abstractmethod
    def get(self, key, sentinel):
        """Gets an item in the cache.

        The `sentinel` passed in is returned if nothing is found in the cache.

        :param key:
            The key to search for in the cache.
        :param sentinel:
            The object to return if key not found in the cache.
        :type key: object
        :type sentinel: object
        :return:
            The item if found in the cache, or the `sentinel` if not found.
        :rtype: object
        """

    @abstractmethod
    def put(self, key, value):
        """Puts an item in the cache.

        :param key:
            The cache key to store the item under.
        :param value:
            The item to store in the cache.
        :type key: object
        :type value: object
        """

    @property
    def dynamic_methods(self):
        """A list of additional methods that should be bound to a wrapped function.

        Allows dynamically binding additional methods to a wrapped function outside of the typical list of methods.

        :return:
            A list of method names that will should be bound to a wrapped function.
        :rtype: list[str]
        """
        return []

    def create_key(self, args, kwargs, typed=False, kwarg_mark=(object(),),
                   fast_types={int, str, frozenset, type(None)}):
        """Creates a cache key from optionally typed positional and keyword arguments.

        Borrowed from `functools`: https://docs.python.org/3/library/functools.html

        :param args:
            A tuple of arguments to use in the key.
        :param kwargs:
            A dictionary of keyword arguments to use in the key.
        :param typed:
            A boolean indicating whether to include typing information in the key.
        :param kwarg_mark:
            Separator object between arguments and keyword arguments.
        :param fast_types:
            A tuple of types that are known to cache their hash values.
        :type args: tuple
        :type kwargs: dict
        :type typed: bool
        :type kwarg_mark: tuple
        :type fast_types: tuple
        """
        key = args
        if kwargs:
            key += kwarg_mark
            for item in kwargs.items():
                key += item
        if typed:
            key += tuple(type(v) for v in args)
            if kwargs:
                key += tuple(type(v) for v in kwargs.values())
        elif len(key) == 1 and type(key[0]) in fast_types:
            return key[0]
        return _HashList(key)


class FIFOCache(BaseCache):
    """First-in First-out cache.

    A First-in First-out cache where keys are evicted in order of arrival when the cache is full. Accessing a key does
    not change the order of eviction. This uses the `deque` class for O(1) access and insertion time.

    :param size:
        The size of the cache. Once full, items are evicted in a FIFO manner.
    :type size: int
    """
    def __init__(self, size):
        super().__init__()
        self._max_size = size
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._map = {}
        self._queue = deque()

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._max_size < 1:
            raise ValueError('size should be > 0')

    @property
    def current_size(self):
        return len(self._map)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return self._max_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._map.clear()
            self._queue.clear()

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            if key in self._map:
                self._hits += 1
                return self._map[key]

            self._misses += 1
            return sentinel

    def put(self, key, value):
        with self._lock:
            if key not in self._map:
                if len(self._map) >= self._max_size:
                    self._map.pop(self._queue.pop())
                self._queue.appendleft(key)
            self._map[key] = value


class LFUCache(BaseCache):
    """Least Frequently Used cache.

    A Least Frequently Used cache where keys which have been accessed the least number of times are evicted when the
    cache is full. This uses a frequency list structure as described in "http://dhruvbird.com/lfu.pdf" for O(1) access
    and insertion time.

    :param size:
        The size of the cache. Once full, the least frequently accessed item is evicted.
    :type size: int
    """
    def __init__(self, size):
        super().__init__()
        self._max_size = size
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._map = {}
        self._freq_list = _FreqList(_FrequencyNode)

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._max_size < 1:
            raise ValueError('size should be > 0')

    @property
    def current_size(self):
        return len(self._map)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return self._max_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._map.clear()
            self._freq_list.clear()

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            if key in self._map:
                self._hits += 1
                frequency_node = self._freq_list.access(self._map[key].frequency_node, key)
                self._map[key].frequency_node = frequency_node
                return self._map[key].value

            self._misses += 1
            return sentinel

    def put(self, key, value):
        with self._lock:
            if key in self._map:
                self._map[key].value = value
                frequency_node = self._freq_list.access(self._map[key].frequency_node, key)
                self._map[key].frequency_node = frequency_node
            else:
                if len(self._map) >= self._max_size:
                    self._map.pop(self._freq_list.pop_left())

                frequency_node = self._freq_list.append(key)
                self._map[key] = _FrequencyData(value, frequency_node)


class LRUCache(BaseCache):
    """Least Recently Used cache.

    A Least Recently Used cache where keys which have been accessed the least recently are evicted when the cache is
    full. A linked list is used to yield O(1) access and insertion time.

    :param size:
        The size of the cache. Once full, the least recently accessed item is evicted.
    :type size: int
    """
    def __init__(self, size):
        super().__init__()
        self._max_size = size
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._map = {}
        self._queue = _LinkedList(_KeyNode)

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._max_size < 1:
            raise ValueError('size should be > 0')

    @property
    def current_size(self):
        return len(self._map)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return self._max_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._map.clear()
            self._queue.clear()

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            if key in self._map:
                self._hits += 1
                self._queue.access(self._map[key].node)
                return self._map[key].value

            self._misses += 1
            return sentinel

    def put(self, key, value):
        with self._lock:
            if key in self._map:
                self._map[key].value = value
                self._queue.access(self._map[key].node)
            else:
                if len(self._map) >= self._max_size:
                    self._map.pop(self._queue.pop().key)

                node = self._queue.append(key)
                self._map[key] = _NodeData(value, node)


class MFUCache(BaseCache):
    """Most Frequently Used cache.

    A Most Frequently Used cache where keys which have been accessed the most number of times are evicted when the
    cache is full. This uses a frequency list structure as described in "http://dhruvbird.com/lfu.pdf" for O(1) access
    and insertion time.

    :param size:
        The size of the cache. Once full, the most frequently accessed item is evicted.
    :type size: int
    """
    def __init__(self, size):
        super().__init__()
        self._max_size = size
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._map = {}
        self._freq_list = _FreqList(_FrequencyNode)

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._max_size < 1:
            raise ValueError('size should be > 0')

    @property
    def current_size(self):
        return len(self._map)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return self._max_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._map.clear()
            self._freq_list.clear()

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            if key in self._map:
                self._hits += 1
                frequency_node = self._freq_list.access(self._map[key].frequency_node, key)
                self._map[key].frequency_node = frequency_node
                return self._map[key].value

        self._misses += 1
        return sentinel

    def put(self, key, value):
        with self._lock:
            if key in self._map:
                self._map[key].value = value
                frequency_node = self._freq_list.access(self._map[key].frequency_node, key)
                self._map[key].frequency_node = frequency_node
            else:
                if len(self._map) >= self._max_size:
                    self._map.pop(self._freq_list.pop())

                frequency_node = self._freq_list.append(key)
                self._map[key] = _FrequencyData(value, frequency_node)


class MQCache(BaseCache):
    """Multi-Queue cache.

    A Multi-Queue cache in which multiple queues are used to hold levels of varying temperature (i.e. highly accessed
    and less accessed) along with a history buffer (similar to 2Q). This is implemented based on the paper "The
    Multi-Queue Replacement Algorithm for Second Level Buffer Caches" which uses a LRU queues for each level. The access
    count of each item is also recorded and used in determining which queue to promote the item to based on the
    `queue_func` parameter.

    Items are also susceptible to being evicted over time. If an item isn't accessed within a certain time it is bumped
    down to a lower queue and its expiration time is reset. This continues if the item isn't accessed until it is
    eventually evicted to the lowest queue.

    The history buffer is a FIFO queue that keeps track of items recently evicted from the queue. If an item is accessed
    while in the history buffer, it is placed in the appropriate queue based on it's previous access frequency + 1.

    The implementation for this algorithm provides for O(1) access and insertion time.

    :param size:
        The size of the cache. Once full, the least recently accessed item in the lowest non-empty queue is moved into
        the buffer.
    :param buffer_size:
        The size of the buffer. Once full, items are evicted in a FIFO manner.
    :param expire_time:
        The minimum number of accesses required to stay in cache if `access_based` is True, otherwise the time in
        seconds.
    :param num_queues:
        The number of queues to use. Defaults to 8.
    :param queue_func:
        A function that determines which queue to insert a node based on it's frequency. Defaults to `log(freq, 2)`.
    :param access_based:
        Whether the "time" should be based on accesses (i.e. each access increments time by 1) or by actual time.
        Defaults to False.
    :type size: int
    :type buffer_size: int
    :type expire_time: int
    :type num_queues: int
    :type queue_func: function
    :type access_based: bool
    """
    def __init__(self, size, buffer_size, expire_time, num_queues=8, queue_func=lambda f: math.log(f, 2),
                 access_based=True):
        super().__init__()
        self._max_size = size
        self._buffer_size = buffer_size
        self._expire_time = expire_time
        self._num_queues = num_queues
        self._queue_func = queue_func
        self._access_based = access_based
        self._current_time = 0
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._map = {}
        self._buffer_map = {}
        self._queues = [_LinkedList(_ExpiryNode) for _ in range(num_queues)]
        self._buffer_queue = _LinkedList(_ExpiryNode)

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._max_size < 1:
            raise ValueError('size should be > 0')

        if self._buffer_size < 1:
            raise ValueError('buffer_size should be > 0')

        if self._expire_time < 1:
            raise ValueError('expire_time should be > 0')

        if self._num_queues < 1:
            raise ValueError('num_queues should be > 0')

    @property
    def current_size(self):
        return len(self._map) + len(self._buffer_map)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return self._max_size + self._buffer_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._map.clear()
            self._buffer_map.clear()
            self._buffer_queue.clear()
            list(map(lambda x: x.clear(), self._queues))

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            self._current_time = self._current_time + 1 if self._access_based else time()

            if key in self._map:
                self._hits += 1

                # Remove item from current queue
                item = self._map[key]
                queue = self._get_queue(item.frequency)
                self._queues[queue].remove(item.node)
            elif key in self._buffer_map:
                self._hits += 1

                # Remove item from buffer
                item = self._buffer_map.pop(key)
                self._buffer_queue.remove(item.node)

                # If key in buffer map, then map has to be full
                self._evict_block()
            else:
                self._misses += 1
                return sentinel

            # Add item to queue
            item.frequency += 1
            expire_time = self._current_time + self._expire_time
            queue = self._get_queue(item.frequency)
            item.node = self._queues[queue].append(key, expire_time)

            # Add item to map
            self._map[key] = item

            # Demote items to below queues if not accessed within life time
            self._adjust()

            return item.value

    def put(self, key, value):
        with self._lock:
            self._current_time = self._current_time if self._access_based else time()

            if key in self._map:
                item = self._map[key]
                item.value = value

                # Remove item from current queue
                queue = self._get_queue(item.frequency)
                self._queues[queue].remove(item.node)
            elif key in self._buffer_map:
                # Remove item from buffer
                item = self._buffer_map.pop(key)
                self._buffer_queue.remove(item.node)
                item.value = value
            else:
                item = _MQData(value, 0, None)

            # Make room if cache is full
            if len(self._map) >= self._max_size:
                self._evict_block()

            # Add item to queue
            item.frequency += 1
            expire_time = self._current_time + self._expire_time
            queue = self._get_queue(item.frequency)
            item.node = self._queues[queue].append(key, expire_time)

            # Add item to map
            self._map[key] = item

            # Demote items to below queues if not accessed within life time
            self._adjust()

    def _adjust(self):
        for k in range(1, self._num_queues):
            node = self._queues[k].peek()
            while node and node.expire_time < self._current_time:
                key = self._queues[k].pop().key
                expire_time = self._current_time + self._expire_time
                self._queues[k-1].append(key, expire_time)
                node = self._queues[k].peek()

    def _evict_block(self):
        non_empty_queue = self._find_non_empty_queue()
        if non_empty_queue > -1:
            # Reduce buffer if full
            if len(self._buffer_map) >= self._buffer_size:
                self._buffer_map.pop(self._buffer_queue.pop().key)

            # Remove victim from queue map
            key = self._queues[non_empty_queue].pop().key
            item = self._map.pop(key)

            # Add victim to history buffer
            expire_time = self._current_time + self._expire_time
            item.node = self._buffer_queue.append(key, expire_time)
            self._buffer_map[key] = item

    def _find_non_empty_queue(self):
        for k in range(self._num_queues):
            if len(self._queues[k]) > 0:
                return k
        return -1

    def _get_queue(self, frequency):
        return min(int(self._queue_func(frequency)), self._num_queues - 1)


class MRUCache(BaseCache):
    """Most Recently Used cache.

    A Most Recently Used cache where keys which have been accessed the most recently are evicted when the cache is
    full. A linked list is used which evicts from the head, appends at the head, and moves accesses to the head, yields
    for O(1) access and insertion time.

    :param size:
        The size of the cache. Once full, the most recently accessed item is evicted.
    :type size: int
    """
    def __init__(self, size):
        super().__init__()
        self._max_size = size
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._map = {}
        self._queue = _LinkedList(_KeyNode)

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._max_size < 1:
            raise ValueError('size should be > 0')

    @property
    def current_size(self):
        return len(self._map)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return self._max_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._map.clear()
            self._queue.clear()

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            if key in self._map:
                self._hits += 1
                self._queue.access(self._map[key].node)
                return self._map[key].value

            self._misses += 1
            return sentinel

    def put(self, key, value):
        with self._lock:
            if key in self._map:
                self._map[key].value = value
                self._queue.access(self._map[key].node)
            else:
                if len(self._map) >= self._max_size:
                    self._map.pop(self._queue.pop_left().key)

                node = self._queue.append(key)
                self._map[key] = _NodeData(value, node)


class NMRUCache(BaseCache):
    """Not Most Recently Used cache.

    A Not Most Recently Used cache where keys which have not been accessed the most recently are evicted when the cache
    is full. When the cache is full, a random key other than the most recently inserted is removed. A hash map is used
    to keep track of cached items for O(1) access and insertion time.

    :param size:
        The size of the cache. Once full, one of the not most recently accessed item is evicted.
    :type size: int
    """
    def __init__(self, size):
        super().__init__()
        self._max_size = size
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._store = {}
        self._mru_item = None

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._max_size < 1:
            raise ValueError('size should be > 0')

    @property
    def current_size(self):
        # Current size should include mru item
        return 0 if self._mru_item is None else len(self._store) + 1

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return self._max_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._store.clear()
            self._mru_item = None

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            if self._mru_item and key == self._mru_item.key:
                self._hits += 1
                return self._mru_item.value

            if key in self._store:
                self._hits += 1
                self._store[self._mru_item.key] = self._mru_item.value
                self._mru_item = _KeyValue(key, self._store.pop(key))
                return self._mru_item.value

            self._misses += 1
            return sentinel

    def put(self, key, value):
        with self._lock:
            if self._mru_item and key == self._mru_item.key:
                self._mru_item.value = value
            elif key in self._store:
                self._store[self._mru_item.key] = self._mru_item.value
                self._mru_item = _KeyValue(key, self._store.pop(key))
            else:
                # Current size should include mru item
                if len(self._store) + 1 >= self._max_size > 1:
                        self._store.popitem()

                # Move mru item to store if exists
                if self._mru_item and self._max_size > 1:
                    self._store[self._mru_item.key] = self._mru_item.value

                self._mru_item = _KeyValue(key, value)


class RRCache(BaseCache):
    """Random replacement cache.

    A Random replacement cache where keys are evicted randomly, regardless of access or insertion order. This uses a
    simple hashmap for O(1) access and insertion time.

    :param size:
        The size of the cache. Once full, items are evicted randomly.
    :type size: int
    """
    def __init__(self, size):
        super().__init__()
        self._max_size = size
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._store = {}

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._max_size < 1:
            raise ValueError('size should be > 0')

    @property
    def current_size(self):
        return len(self._store)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return self._max_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._store.clear()

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            if key in self._store:
                self._hits += 1
                return self._store[key]

            self._misses += 1
            return sentinel

    def put(self, key, value):
        with self._lock:
            if key in self._store:
                self._store[key] = value
            else:
                if len(self._store) >= self._max_size:
                    self._store.popitem()

                self._store[key] = value


class SLRUCache(BaseCache):
    """Segmented Least Recently Used cache.

    A Segmented Least Recently Used cache which is implemented with two queues, a LRU (the protected), and a FIFO (the
    probationary). Items are initially placed into the probationary queue when first placed into the cache. If this
    cache is full, items are evicted in the order of their arrival. If items are accessed while they are in the
    probationary queue, they are moved to the protected queue. They stay in this queue until it is full and the key
    which has been least recently used is moved back to the probationary queue. This implementation yields O(1) access
    and insertion time.

    Note that this cache implementation is very similar to the simple 2Q algorithm with the exception that items evicted
    from the protected cache are moved to the probationary (opposed to being immediately evicted).

    :param protected_size:
        The size of the protected cache. Once full, the least recently accessed item is moved to the probationary queue.
    :param probationary_size:
        The size of the probationary cache. Once full, items are evicted in a FIFO manner.
    :type protected_size: int
    :type probationary_size: int
    """
    def __init__(self, protected_size, probationary_size):
        super().__init__()
        self._protected_size = protected_size
        self._probationary_size = probationary_size
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._probationary_map = {}
        self._protected_map = {}
        self._probationary_store = _LinkedList(_KeyNode)
        self._protected_store = _LinkedList(_KeyNode)

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._protected_size < 1:
            raise ValueError('protected_size should be > 0')

        if self._probationary_size < 1:
            raise ValueError('probationary_size should be > 0')

    @property
    def current_size(self):
        return len(self._probationary_map) + len(self._protected_map)

    @property
    def hits(self):
        return self._hits

    @property
    def misses(self):
        return self._misses

    @property
    def max_size(self):
        return self._probationary_size + self._protected_size

    def clear(self):
        with self._lock:
            self._probationary_map.clear()
            self._protected_map.clear()
            self._probationary_store.clear()
            self._protected_store.clear()

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            # Protected is 'hot' cache, i.e. more likely to be found here
            if key in self._protected_map:
                self._hits += 1
                self._protected_store.access(self._protected_map[key].node)
                return self._protected_map[key].value

            # Probationary cache hits move to protected
            if key in self._probationary_map:
                self._hits += 1
                o = self._probationary_map.pop(key)
                self._probationary_store.remove(o.node)
                value = o.value

                # If protected is full, move LRU to probationary
                if len(self._protected_map) >= self._protected_size:
                    other_key = self._protected_store.pop().key
                    other_value = self._protected_map.pop(other_key).value

                    # Probationary won't be full because we just evicted from it

                    other_node = self._probationary_store.append(other_key)
                    self._probationary_map[other_key] = _NodeData(other_value, other_node)

                node = self._protected_store.append(key)
                self._protected_map[key] = _NodeData(value, node)
                return value

            self._misses += 1
            return sentinel

    def put(self, key, value):
        with self._lock:
            if key in self._protected_map:
                self._protected_map[key].value = value
                self._protected_store.access(self._protected_map[key].node)

            # Probationary cache hits move to protected
            elif key in self._probationary_map:
                node = self._probationary_map.pop(key).node
                self._probationary_store.remove(node)

                # If protected is full, move LRU to probationary
                if len(self._protected_map) >= self._protected_size:
                    other_key = self._protected_store.pop().key
                    other_value = self._protected_map.pop(other_key).value

                    # Probationary won't be full because we just evicted from it

                    other_node = self._probationary_store.append(other_key)
                    self._probationary_map[other_key] = _NodeData(other_value, other_node)

                node = self._protected_store.append(key)
                self._protected_map[key] = _NodeData(value, node)

            # Place in probationary
            else:
                # If probationary is full, evict LRU
                if len(self._probationary_map) >= self._probationary_size:
                    self._probationary_map.pop(self._probationary_store.pop().key)

                node = self._probationary_store.append(key)
                self._probationary_map[key] = _NodeData(value, node)


class StaticCache(BaseCache):
    """Static cache.

    A simple cache with no key eviction. The implementation is a simple key/value store with O(1) access and insertion
    time. Keys are stored permanently, or at least until the cache is cleared.
    """
    def __init__(self):
        super().__init__()
        # Cache info
        self._hits = 0
        self._misses = 0
        self._lock = RLock()

        # Data storage
        self._store = {}

    @property
    def current_size(self):
        return len(self._store)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return math.inf

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            if key in self._store:
                self._hits += 1
                return self._store[key]

        self._misses += 1
        return sentinel

    def put(self, key, value):
        with self._lock:
            self._store[key] = value


class TLRUCache(BaseCache):
    """Time-aware Least Recently Used cache.

    A Time-aware Least-Recently-Used cache where keys are prematurely evicted if their last access time is below a
    minimum limit, the `expire_time`. Time in this case is either a simple clock that is incremented each time the cache
    is accessed., or the actual time in seconds that has passed. This is determined by the `access_based` parameter.
    If `reset_on_access` is True, the `expire_time` is reset each time the item is accessed; otherwise it is expired
    from the time of initial insertion in the cache.

    This is implemented with two LRU lists, one for LRU-based expiration and another for time-based expiration. This
    implementation provides a O(1) time complexity for both accesses and insertions.

    :param expire_time:
        The minimum number of accesses required to stay in cache if `access_based` is True, otherwise the time in
        seconds until forced eviction.
    :param size:
        The size of the cache. Once full, items are evicted based on LRU. If None, the cache grows boundlessly and items
        are only evicted based on access time.
    :param access_based:
        Whether the time should be based on accesses (i.e. each access increments time by 1) or by actual time. Defaults
        to False.
    :param reset_on_access:
        Whether to reset the key's expire time when accessed. Otherwise the key is expired after the `expire time`
        regardless of whether it is accessed or not. Defaults to True.
    :type expire_time: int
    :type size: int, None
    :type access_based: bool
    :type reset_on_access: bool
    """
    def __init__(self, expire_time, size=None, access_based=False, reset_on_access=True):
        super().__init__()
        self._expire_time = expire_time
        self._max_size = size
        self._reset_on_access = reset_on_access
        self._access_based = access_based
        self._current_time = 0
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._map = {}
        self._queue = _LinkedList(_KeyNode) if size else None
        self._access_queue = _LinkedList(_ExpiryNode)

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._expire_time < 1:
            raise ValueError('expire_time should be > 0')

        if self._max_size is not None and self._max_size < 1:
            raise ValueError('size should be > 0 or None')

    @property
    def current_size(self):
        return len(self._map)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        if self._max_size is None:
            return math.inf
        return self._max_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._map.clear()
            self._access_queue.clear()

            if self._queue is not None:
                self._queue.clear()

            self._hits = 0
            self._misses = 0
            self._current_time = 0

    def get(self, key, sentinel):
        with self._lock:
            self._current_time = self._current_time + 1 if self._access_based else time()

            # Remove nodes not accessed within expire time
            self._adjust()

            if key in self._map:
                self._hits += 1

                # If no size, no point in using LRU queue, otherwise move to front of LRU queue
                if self._queue is not None:
                    self._queue.access(self._map[key].queue_node)

                # Move to front of access queue and reset access if enabled
                if self._reset_on_access:
                    self._map[key].access_queue_node.expire_time = self._current_time + self._expire_time
                    self._access_queue.access(self._map[key].access_queue_node)

                return self._map[key].value

            # Remove nodes not accessed within expire time
            self._adjust()

            self._misses += 1
            return sentinel

    def put(self, key, value):
        with self._lock:
            self._current_time = self._current_time if self._access_based else time()

            # Remove nodes not accessed within expire time
            self._adjust()

            if key in self._map:
                self._map[key].value = value

                # If no size, no point in using LRU queue, otherwise move to front of LRU queue
                if self._queue is not None:
                    self._queue.access(self._map[key].queue_node)

                # Move to front of access queue and reset access if enabled
                if self._reset_on_access:
                    self._map[key].access_queue_node.expire_time = self._current_time + self._expire_time
                    self._access_queue.access(self._map[key].access_queue_node)
            else:
                # Remove from LRU queue is over capacity
                if self._max_size and len(self._map) >= self._max_size:
                    other_key = self._queue.pop().key
                    access_queue_node = self._map.pop(other_key).access_queue_node
                    self._access_queue.remove(access_queue_node)

                # Append to LRU queue if bounded by size
                queue_node = None
                if self._queue is not None:
                    queue_node = self._queue.append(key)

                expire_time = self._current_time + self._expire_time
                access_queue_node = self._access_queue.append(key, expire_time)

                self._map[key] = _ExpiryData(value, queue_node, access_queue_node)

    def _adjust(self):
        # Remove items that haven't been accessed within expiration time
        node = self._access_queue.peek()
        while node and node.expire_time < self._current_time:
            key = self._access_queue.pop().key
            queue_node = self._map.pop(key).queue_node

            if self._queue is not None:
                self._queue.remove(queue_node)

            node = self._access_queue.peek()


class TwoQCache(BaseCache):
    """2Q simple cache.

    The simple 2Q cache described by the algorithm in "2Q: A Low Overhead High Performance Buffer Management Replacement
    Algorithm". Two queues are used, an LRU (the primary), and a FIFO (the secondary). Items are initially placed into
    the secondary queue when placed into the cache. If the secondary queue is full, items are evicted in the order of
    their arrival. If items are accessed while they are in the secondary queue, they are moved to the primary queue.
    They stay in this queue until it is full and the key which has been least recently used is evicted. This
    implementation yields O(1) access and insertion time.

    The `max_size` for the cache is the combined size of both the primary and secondary queue as both contain items.

    :param primary_size:
        The size of the primary queue for the cache. Once full, the least recently accessed item is evicted.
    :param secondary_size:
        The size of the secondary queue for the cache. One full, items are evicted in a FIFO manner.
    :type primary_size: int
    :type secondary_size: int
    """
    def __init__(self, primary_size, secondary_size):
        super().__init__()
        self._primary_size = primary_size
        self._secondary_size = secondary_size
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._primary_map = {}
        self._secondary_map = {}
        self._primary_store = _LinkedList(_KeyNode)
        self._secondary_store = _LinkedList(_KeyNode)

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._primary_size < 1:
            raise ValueError('primary_size should be > 0')

        if self._secondary_size < 1:
            raise ValueError('secondary_size should be > 0')

    @property
    def current_size(self):
        return len(self._primary_map) + len(self._secondary_map)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return self._primary_size + self._secondary_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._primary_map.clear()
            self._secondary_map.clear()
            self._primary_store.clear()
            self._secondary_store.clear()

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            # Primary is 'hot' cache, i.e. more likely to be found here
            if key in self._primary_map:
                self._hits += 1
                self._primary_store.access(self._primary_map[key].node)
                return self._primary_map[key].value

            # Secondary cache hits move to primary
            if key in self._secondary_map:
                self._hits += 1
                o = self._secondary_map.pop(key)
                self._secondary_store.remove(o.node)

                # Make room for key in primary queue
                if len(self._primary_map) >= self._primary_size:
                    self._primary_map.pop(self._primary_store.pop().key)

                node = self._primary_store.append(key)
                self._primary_map[key] = _NodeData(o.value, node)
                return o.value

            self._misses += 1
            return sentinel

    def put(self, key, value):
        with self._lock:
            if key in self._primary_map:
                self._primary_map[key].value = value
                self._primary_store.access(self._primary_map[key].node)
            elif key in self._secondary_map:
                self._secondary_map[key].value = value
                self._secondary_store.access(self._secondary_map[key].node)
            else:
                # Make room for key in secondary queue
                if len(self._secondary_map) >= self._secondary_size:
                    self._secondary_map.pop(self._secondary_store.pop().key)

                node = self._secondary_store.append(key)
                self._secondary_map[key] = _NodeData(value, node)


class TwoQFullCache(BaseCache):
    """2Q full cache.

    The full 2Q cache as described by the algorithm in "2Q: A Low Overhead High Performance Buffer Management
    Replacement Algorithm". Three queues are used, an LRU (the primary), and two FIFO (the secondary in and out). Items
    are initially placed into the secondary "in" queue when first placed into the cache. If this queue is full, items
    are moved in the order of their arrival into the secondary "out" queue. If items are accessed while they are in the
    secondary "in" queue they stay in this queue in their current position.

    If items are accessed while they are in the secondary "out" queue they are moved to the primary queue. If this cache
    is full, items are evicted in the order of their arrival. Items in the primary queue stay in this queue until it is
    full and the key which has been least recently used is evicted. This implementation yields O(1) access and insertion
    time.

    The `max_size` for the cache is the size of the primary, secondary "in", and secondary "out" queue as both contain
    items.

    :param primary_size:
        The size of the primary queue for the cache. Once full, the least recently accessed item is evicted.
    :param secondary_in_size:
        The size of the secondary "in" queue for the cache. One full, items are moved to the secondary "in" queue in a
        FIFO manner.
    :param secondary_out_size:
        The size of the secondary "out" queue for the cache. Once full, items are evicted in a FIFO manner.
    :type primary_size: int
    :type secondary_in_size: int
    :type secondary_out_size: int
    """
    def __init__(self, primary_size, secondary_in_size, secondary_out_size):
        super().__init__()
        self._primary_size = primary_size
        self._secondary_in_size = secondary_in_size
        self._secondary_out_size = secondary_out_size
        self._lock = RLock()

        # Cache info
        self._hits = 0
        self._misses = 0

        # Data storage
        self._primary_map = {}
        self._secondary_in_map = {}
        self._secondary_out_map = {}
        self._primary_store = _LinkedList(_KeyNode)
        self._secondary_in_store = _LinkedList(_KeyNode)
        self._secondary_out_store = _LinkedList(_KeyNode)

        # Validate parameters
        self._validations()

    def _validations(self):
        if self._primary_size < 1:
            raise ValueError('primary_size should be > 0')

        if self._secondary_in_size < 1:
            raise ValueError('secondary_in_size should be > 0')

        if self._secondary_out_size < 1:
            raise ValueError('secondary_out_size should be > 0')


    @property
    def current_size(self):
        return len(self._primary_map) + len(self._secondary_in_map) + len(self._secondary_out_map)

    @property
    def hits(self):
        return self._hits

    @property
    def max_size(self):
        return self._primary_size + self._secondary_in_size + self._secondary_out_size

    @property
    def misses(self):
        return self._misses

    def clear(self):
        with self._lock:
            self._primary_map.clear()
            self._secondary_in_map.clear()
            self._secondary_out_map.clear()
            self._primary_store.clear()
            self._secondary_in_store.clear()
            self._secondary_out_store.clear()

            self._hits = 0
            self._misses = 0

    def get(self, key, sentinel):
        with self._lock:
            # Primary is 'hot' cache, i.e. more likely to be found here
            if key in self._primary_map:
                self._hits += 1
                self._primary_store.access(self._primary_map[key].node)
                return self._primary_map[key].value

            # Secondary 'in' cache hits do nothing
            if key in self._secondary_in_map:
                self._hits += 1
                return self._secondary_in_map[key].value

            # Secondary 'out' cache hits move to primary
            if key in self._secondary_out_map:
                self._hits += 1
                o = self._secondary_out_map.pop(key)
                self._secondary_out_store.remove(o.node)

                # Make room for key in primary queue
                if len(self._primary_map) >= self._primary_size:
                    self._primary_map.pop(self._primary_store.pop().key)

                node = self._primary_store.append(key)
                self._primary_map[key] = _NodeData(o.value, node)
                return o.value

            self._misses += 1
            return sentinel

    def put(self, key, value):
        with self._lock:
            if key in self._primary_map:
                self._primary_map[key].value = value
                self._primary_store.access(self._primary_map[key].node)
            elif key in self._secondary_in_map:
                self._secondary_in_map[key].value = value
                self._secondary_in_store.access(self._secondary_in_map[key].node)
            elif key in self._secondary_out_map:
                node = self._secondary_out_map.pop(key).node
                self._secondary_out_store.remove(node)

                # Make room for key in primary queue
                if len(self._primary_map) >= self._primary_size:
                    self._primary_map.pop(self._primary_store.pop().key)

                node = self._primary_store.append(key)
                self._primary_map[key] = _NodeData(value, node)
            else:
                # Make room for key in secondary "in" queue
                if len(self._secondary_in_map) >= self._secondary_in_size:
                    other_key = self._secondary_in_store.pop().key
                    o = self._secondary_in_map.pop(other_key)

                    # Make room for other key in secondary "out" queue
                    if len(self._secondary_out_map) >= self._secondary_out_size:
                        self._secondary_out_map.pop(self._secondary_out_store.pop().key)

                    other_node = self._secondary_out_store.append(other_key)
                    self._secondary_out_map[other_key] = _NodeData(o.value, other_node)

                node = self._secondary_in_store.append(key)
                self._secondary_in_map[key] = _NodeData(value, node)
