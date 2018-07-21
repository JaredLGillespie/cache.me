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

import unittest
from unittest.mock import Mock
from cachme import *


class NoCache(BaseCache):
    @property
    def current_size(self): return 0
    @property
    def hits(self): return 0
    def max_size(self): return 0
    def misses(self): return 0
    def clear(self): pass
    def get(self, key, sentinel): pass
    def put(self, key, value): pass


class TestCache(unittest.TestCase):

    def test_run_creates_key(self):
        algo = Mock()
        algo.dynamic_methods = []

        cache(algo)(lambda x: x)(1)
        algo.create_key.assert_called_once_with((1,), {}, False)

    def test_run_uses_cache_value_if_available(self):
        algo = Mock()
        algo.dynamic_methods = []
        algo.get.return_value = 0

        out = cache(algo)(lambda x: x)(1)
        self.assertEqual(0, out)

    def test_run_calls_func_if_not_in_cache(self):
        def get(sentinel, key): return sentinel

        algo = Mock()
        algo.dynamic_methods = []
        algo.get = get

        out = cache(algo)(lambda x: x)(1)
        self.assertEqual(1, out)

    def test_cache_info(self):
        algo = Mock()
        algo.dynamic_methods = []
        algo.hits = 1
        algo.misses = 2
        algo.max_size = 3
        algo.current_size = 4

        out = cache(algo)(lambda x: x).cache_info()

        self.assertEqual(1, out.hits)
        self.assertEqual(2, out.misses)
        self.assertEqual(3, out.max_size)
        self.assertEqual(4, out.current_size)

    def test_cache_clear(self):
        algo = Mock()
        algo.dynamic_methods = []

        cache(algo)(lambda x: x).cache_clear()

        self.assertEqual(1, algo.clear.call_count)

    def test_dynamic_methods(self):
        def method_1(): return 1
        def method_2(): return 2

        algo = Mock()
        algo.dynamic_methods = ['method_1', 'method_2']
        algo.method_1 = method_1
        algo.method_2 = method_2

        func = cache(algo)(lambda x: x)

        self.assertEqual(func.cache_method_1, method_1)
        self.assertEqual(func.cache_method_2, method_2)

    def test_on_hit_args(self):
        call = Mock()
        algo = Mock()
        algo.dynamic_methods = []
        algo.hits = 1

        def on_hit(hits, *args):
            self.assertEqual(1, len(args))
            self.assertEqual(2, args[0])
            call(hits)

        cache(algo, on_hit=on_hit)(lambda x: x)(2)
        call.assert_called_once_with(1)

    def test_on_hit_args_and_kwargs(self):
        call = Mock()
        algo = Mock()
        algo.dynamic_methods = []
        algo.hits = 1

        def on_hit(hits, *args, **kwargs):
            self.assertEqual(1, len(args))
            self.assertEqual(2, args[0])
            self.assertEqual(1, len(kwargs))
            self.assertEqual(True, kwargs['nothing'])
            call(hits)

        cache(algo, on_hit=on_hit)(lambda x: x)(2, nothing=True)
        call.assert_called_once_with(1)

    def test_on_hit_kwarg_only_params(self):
        call = Mock()
        algo = Mock()
        algo.dynamic_methods = []
        algo.hits = 1

        def on_hit(*args, x=1, **kwargs):
            call(args[0])

        cache(algo, on_hit=on_hit)(lambda x: x)(2)
        call.assert_called_once_with(1)

    def test_on_hit_no_params(self):
        call = Mock()
        algo = Mock()
        algo.dynamic_methods = []
        algo.hits = 1

        def on_hit():
            call()

        cache(algo, on_hit=on_hit)(lambda x: x)(2)
        call.assert_called_once_with()

    def test_on_hit_params(self):
        call = Mock()
        algo = Mock()
        algo.dynamic_methods = []
        algo.hits = 1

        def on_hit(x):
            call(1)

        cache(algo, on_hit=on_hit)(lambda x: x)(2)
        call.assert_called_once_with(1)

    def test_on_miss_args(self):
        def get(sentinel, key): return sentinel
        def func(*args, **kwargs): return 3

        call = Mock()
        algo = Mock()
        algo.dynamic_methods = []
        algo.get = get
        algo.misses = 1

        def on_miss(misses, *args):
            self.assertEqual(1, len(args))
            self.assertEqual(2, args[0])
            call(misses)

        cache(algo, on_miss=on_miss)(func)(2)
        call.assert_called_once_with(1)

    def test_on_miss_args_and_kwargs(self):
        def get(sentinel, key): return sentinel
        def func(*args, **kwargs): return 3

        call = Mock()
        algo = Mock()
        algo.dynamic_methods = []
        algo.get = get
        algo.misses = 1

        def on_miss(misses, *args, **kwargs):
            self.assertEqual(1, len(args))
            self.assertEqual(2, args[0])
            self.assertEqual(1, len(kwargs))
            self.assertEqual(True, kwargs['nothing'])
            call(misses)

        cache(algo, on_miss=on_miss)(func)(2, nothing=True)
        call.assert_called_once_with(1)

    def test_on_miss_kwarg_only_params(self):
        def get(sentinel, key): return sentinel

        call = Mock()
        algo = Mock()
        algo.dynamic_methods = []
        algo.get = get
        algo.misses = 1

        def on_miss(*args, x=1, **kwargs):
            call(args[0])

        cache(algo, on_miss=on_miss)(lambda x: x)(2)
        call.assert_called_once_with(1)

    def test_on_miss_no_params(self):
        def get(sentinel, key): return sentinel

        call = Mock()
        algo = Mock()
        algo.dynamic_methods = []
        algo.get = get
        algo.misses = 1

        def on_miss():
            call()

        cache(algo, on_miss=on_miss)(lambda x: x)(2)
        call.assert_called_once_with()

    def test_on_miss_params(self):
        def get(sentinel, key): return sentinel

        call = Mock()
        algo = Mock()
        algo.dynamic_methods = []
        algo.get = get
        algo.misses = 1

        def on_miss(x):
            call(1)

        cache(algo, on_miss=on_miss)(lambda x: x)(2)
        call.assert_called_once_with(1)

    def test_miss_puts_key(self):
        def get(sentinel, key): return sentinel
        def func(): return 3

        algo = Mock()
        algo.dynamic_methods = []
        algo.get = get
        algo.create_key.return_value = 'key'

        cache(algo)(func)()
        algo.put.assert_called_once_with('key', 3)

    def test_func_with_args_only(self):
        def get(sentinel, key): return sentinel
        def func(*args): return 3

        algo = Mock()
        algo.dynamic_methods = []
        algo.get = get

        out = cache(algo)(func)(2)
        self.assertEqual(3, out)

    def test_func_with_kwargs_only(self):
        def get(sentinel, key): return sentinel
        def func(**kwargs): return 3

        algo = Mock()
        algo.dynamic_methods = []
        algo.get = get

        out = cache(algo)(func)(a=2)
        self.assertEqual(3, out)

    def test_func_with_args_and_kwargs(self):
        def get(sentinel, key): return sentinel
        def func(*args, **kwargs): return 3

        algo = Mock()
        algo.dynamic_methods = []
        algo.get = get

        out = cache(algo)(func)(2, a=4)
        self.assertEqual(3, out)

    def test_key_func(self):
        algo = Mock()
        algo.dynamic_methods = []

        cache(algo, key_func=lambda x: ((0,), {}))(lambda x: x)(1)
        algo.create_key.assert_called_once_with((0,), {}, False)


class TestBaseCache(unittest.TestCase):

    def test_create_key_args_only(self):
        obj = object()
        expected = [1, 2, 3, obj]
        actual = NoCache().create_key((1, 2, 3, obj), {})
        self.assertEqual(expected, actual)

    def test_dynamic_methods(self):
        actual = NoCache().dynamic_methods
        self.assertEqual([], actual)

    def test_create_key_kwargs_only(self):
        expected = ['a', 1, 'b', 2]
        actual = NoCache().create_key((), kwargs={'a': 1, 'b': 2}, kwarg_mark=())
        self.assertEqual(expected, actual)

    def test_create_key_args_and_kwargs(self):
        obj = object()
        expected = [1, 2, 3, obj, 'a', 4, 'b', 5]
        actual = NoCache().create_key((1, 2, 3, obj), {'a': 4, 'b': 5}, kwarg_mark=())
        self.assertEqual(expected, actual)

    def test_create_key_fasttypes(self):
        expected = 1
        actual = NoCache().create_key((1,), {})
        self.assertEqual(expected, actual)

    def test_create_key_args_typed(self):
        obj = object()
        expected = [1, 2, 3, obj, int, int, int, object]
        actual = NoCache().create_key((1, 2, 3, obj), {}, typed=True)
        self.assertEqual(expected, actual)

    def test_create_key_kwargs_typed(self):
        expected = ['a', 1, 'b', 2, int, int]
        actual = NoCache().create_key((), {'a': 1, 'b': 2}, typed=True, kwarg_mark=())
        self.assertEqual(expected, actual)

    def test_create_key_rehashes_correctly(self):
        actual = NoCache().create_key((), kwargs={'a': 1, 'b': 2}, kwarg_mark=())
        self.assertEqual(hash(actual), hash(actual))


class TestFIFOCache(unittest.TestCase):

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            FIFOCache(0)

    def test_current_size_when_empty(self):
        fc = FIFOCache(1)
        self.assertEqual(0, fc.current_size)

    def test_current_size_with_items(self):
        fc = FIFOCache(2)
        fc.put('key1', 1)
        fc.put('key2', 2)
        self.assertEqual(2, fc.current_size)

    def test_current_size_with_full_cache(self):
        fc = FIFOCache(2)
        fc.put('key1', 1)
        fc.put('key2', 2)
        self.assertEqual(2, fc.current_size)

    def test_max_size(self):
        fc = FIFOCache(1)
        self.assertEqual(1, fc.max_size)

    def test_hits_none(self):
        fc = FIFOCache(1)
        fc.get('key', object())
        fc.get('key', object())
        self.assertEqual(0, fc.hits)

    def test_hits_some(self):
        fc = FIFOCache(2)
        fc.put('key', object())
        fc.get('key', object())
        fc.get('key', object())
        self.assertEqual(2, fc.hits)

    def test_misses(self):
        fc = FIFOCache(1)
        fc.get('key', object())
        fc.get('key', object())
        self.assertEqual(2, fc.misses)

    def test_misses_none(self):
        fc = FIFOCache(2)
        fc.put('key', object())
        fc.get('key', object())
        fc.get('key', object())
        self.assertEqual(0, fc.misses)

    def test_clear_with_empty_cache(self):
        fc = FIFOCache(1)
        fc.clear()
        self.assertEqual({}, fc._map)
        self.assertEqual(0, len(fc._queue))
        self.assertEqual(0, fc.hits)
        self.assertEqual(0, fc.misses)

    def test_clear_with_items(self):
        fc = FIFOCache(1)
        fc.put('key1', 1)
        fc.put('key2', 2)
        fc.clear()
        self.assertEqual({}, fc._map)
        self.assertEqual(0, len(fc._queue))
        self.assertEqual(0, fc.hits)
        self.assertEqual(0, fc.misses)

    def test_get_key_in_cache(self):
        fc = FIFOCache(1)
        fc.put('key', 1)
        out = fc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        fc = FIFOCache(1)
        sentinel = object()
        out = fc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        fc = FIFOCache(1)
        fc.put('key', 1)
        out = fc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, fc.hits)
        self.assertEqual(0, fc.misses)

    def test_put_existing_key_in_cache(self):
        fc = FIFOCache(1)
        fc.put('key', 1)
        fc.put('key', 2)
        out = fc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, fc.hits)
        self.assertEqual(0, fc.misses)

    def test_key_evicts_when_full(self):
        sentinel = object()
        fc = FIFOCache(2)
        fc.put('key1', 1)
        fc.put('key2', 2)
        out1 = fc.get('key1', sentinel)

        # key2 gets evicted
        fc.put('key3', 3)

        # key1 gets evicted
        fc.put('key4', 4)
        out2 = fc.get('key2', sentinel)
        out3 = fc.get('key3', sentinel)
        out4 = fc.get('key4', sentinel)
        out5 = fc.get('key1', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(sentinel, out2)
        self.assertEqual(3, out3)
        self.assertEqual(4, out4)
        self.assertEqual(sentinel, out5)


class TestLIFOCache(unittest.TestCase):

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            LIFOCache(0)

    def test_current_size_when_empty(self):
        lc = LIFOCache(1)
        self.assertEqual(0, lc.current_size)

    def test_current_size_with_items(self):
        lc = LIFOCache(2)
        lc.put('key1', 1)
        lc.put('key2', 2)
        self.assertEqual(2, lc.current_size)

    def test_current_size_with_full_cache(self):
        lc = LIFOCache(2)
        lc.put('key1', 1)
        lc.put('key2', 2)
        self.assertEqual(2, lc.current_size)

    def test_max_size(self):
        lc = LIFOCache(1)
        self.assertEqual(1, lc.max_size)

    def test_hits_none(self):
        lc = LIFOCache(1)
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(0, lc.hits)

    def test_hits_some(self):
        lc = LIFOCache(2)
        lc.put('key', object())
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(2, lc.hits)

    def test_misses(self):
        lc = LIFOCache(1)
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(2, lc.misses)

    def test_misses_none(self):
        lc = LIFOCache(2)
        lc.put('key', object())
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(0, lc.misses)

    def test_clear_with_empty_cache(self):
        lc = LIFOCache(1)
        lc.clear()
        self.assertEqual({}, lc._map)
        self.assertEqual(0, len(lc._queue))
        self.assertEqual(0, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_clear_with_items(self):
        lc = LIFOCache(1)
        lc.put('key1', 1)
        lc.put('key2', 2)
        lc.clear()
        self.assertEqual({}, lc._map)
        self.assertEqual(0, len(lc._queue))
        self.assertEqual(0, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_get_key_in_cache(self):
        lc = LIFOCache(1)
        lc.put('key', 1)
        out = lc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        lc = LIFOCache(1)
        sentinel = object()
        out = lc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        lc = LIFOCache(1)
        lc.put('key', 1)
        out = lc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_put_existing_key_in_cache(self):
        lc = LIFOCache(1)
        lc.put('key', 1)
        lc.put('key', 2)
        out = lc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_key_evicts_when_full(self):
        sentinel = object()
        lc = LIFOCache(2)
        lc.put('key1', 1)
        lc.put('key2', 2)
        out1 = lc.get('key1', sentinel)

        # key2 gets evicted
        lc.put('key3', 3)

        # key3 gets evicted
        lc.put('key4', 4)
        out2 = lc.get('key2', sentinel)
        out3 = lc.get('key3', sentinel)
        out4 = lc.get('key4', sentinel)
        out5 = lc.get('key1', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(sentinel, out2)
        self.assertEqual(sentinel, out3)
        self.assertEqual(4, out4)
        self.assertEqual(1, out5)


class TestLFUCache(unittest.TestCase):

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            LFUCache(0)

    def test_current_size_when_empty(self):
        lc = LFUCache(1)
        self.assertEqual(0, lc.current_size)

    def test_current_size_with_items(self):
        lc = LFUCache(2)
        lc.put('key1', 1)
        lc.put('key2', 2)
        self.assertEqual(2, lc.current_size)

    def test_current_size_with_full_cache(self):
        lc = LFUCache(2)
        lc.put('key1', 1)
        lc.put('key2', 2)
        self.assertEqual(2, lc.current_size)

    def test_max_size(self):
        lc = LFUCache(1)
        self.assertEqual(1, lc.max_size)

    def test_hits_none(self):
        lc = LFUCache(1)
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(0, lc.hits)

    def test_hits_some(self):
        lc = LFUCache(2)
        lc.put('key', object())
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(2, lc.hits)

    def test_misses(self):
        lc = LFUCache(1)
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(2, lc.misses)

    def test_misses_none(self):
        lc = LFUCache(2)
        lc.put('key', object())
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(0, lc.misses)

    def test_clear_with_empty_cache(self):
        lc = LFUCache(1)
        lc.clear()
        self.assertEqual({}, lc._map)
        self.assertEqual(0, len(lc._freq_list))
        self.assertEqual(0, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_clear_with_items(self):
        lc = LFUCache(1)
        lc.put('key1', 1)
        lc.put('key2', 2)
        lc.clear()
        self.assertEqual({}, lc._map)
        self.assertEqual(0, len(lc._freq_list))
        self.assertEqual(0, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_get_key_in_cache(self):
        lc = LFUCache(1)
        lc.put('key', 1)
        out = lc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        lc = LFUCache(1)
        sentinel = object()
        out = lc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        lc = LFUCache(1)
        lc.put('key', 1)
        out = lc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_put_existing_key_in_cache(self):
        lc = LFUCache(1)
        lc.put('key', 1)
        lc.put('key', 2)
        out = lc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_key_evicts_when_full(self):
        sentinel = object()
        lc = LFUCache(1)
        lc.put('key1', 1)
        lc.put('key2', 2)
        out1 = lc.get('key1', sentinel)
        out2 = lc.get('key2', sentinel)
        self.assertEqual(sentinel, out1)
        self.assertEqual(2, out2)

    def test_key_evicts_least_frequent(self):
        sentinel = object()
        lc = LFUCache(3)
        lc.put('key1', 1)
        lc.put('key2', 2)
        lc.put('key3', 3)
        out1 = lc.get('key2', sentinel)
        out2 = lc.get('key1', sentinel)
        out3 = lc.get('key2', sentinel)

        # key3 should be evicted
        lc.put('key4', 4)
        out4 = lc.get('key1', sentinel)

        # key4 should be evicted
        lc.put('key5', 5)
        out5 = lc.get('key2', sentinel)
        out6 = lc.get('key3', sentinel)
        out7 = lc.get('key4', sentinel)
        out8 = lc.get('key5', sentinel)
        out9 = lc.get('key5', sentinel)
        out10 = lc.get('key2', sentinel)
        out11 = lc.get('key5', sentinel)
        self.assertEqual(2, out1)
        self.assertEqual(1, out2)
        self.assertEqual(2, out3)
        self.assertEqual(1, out4)
        self.assertEqual(2, out5)
        self.assertEqual(sentinel, out6)
        self.assertEqual(sentinel, out7)
        self.assertEqual(5, out8)
        self.assertEqual(5, out9)
        self.assertEqual(2, out10)
        self.assertEqual(5, out11)

    def test_key_evicts_random_if_tie(self):
        sentinel = object()
        lc = LFUCache(2)
        lc.put('key1', 1)
        lc.put('key2', 2)
        lc.put('key3', 3)
        out1 = lc.get('key1', sentinel)
        out2 = lc.get('key2', sentinel)
        out3 = lc.get('key3', sentinel)

        self.assertEqual(1, len({1, 2, 3}.difference({out1, out2, out3})))


class TestLRUCache(unittest.TestCase):

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            LRUCache(0)

    def test_current_size_when_empty(self):
        lc = LRUCache(1)
        self.assertEqual(0, lc.current_size)

    def test_current_size_with_items(self):
        lc = LRUCache(2)
        lc.put('key1', 1)
        lc.put('key2', 2)
        self.assertEqual(2, lc.current_size)

    def test_current_size_with_full_cache(self):
        lc = LRUCache(2)
        lc.put('key1', 1)
        lc.put('key2', 2)
        self.assertEqual(2, lc.current_size)

    def test_max_size(self):
        lc = LRUCache(1)
        self.assertEqual(1, lc.max_size)

    def test_hits_none(self):
        lc = LRUCache(1)
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(0, lc.hits)

    def test_hits_some(self):
        lc = LRUCache(2)
        lc.put('key', object())
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(2, lc.hits)

    def test_misses(self):
        lc = LRUCache(1)
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(2, lc.misses)

    def test_misses_none(self):
        lc = LRUCache(2)
        lc.put('key', object())
        lc.get('key', object())
        lc.get('key', object())
        self.assertEqual(0, lc.misses)

    def test_clear_with_empty_cache(self):
        lc = LRUCache(1)
        lc.clear()
        self.assertEqual({}, lc._map)
        self.assertEqual(0, len(lc._queue))
        self.assertEqual(0, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_clear_with_items(self):
        lc = LRUCache(1)
        lc.put('key1', 1)
        lc.put('key2', 2)
        lc.clear()
        self.assertEqual({}, lc._map)
        self.assertEqual(0, len(lc._queue))
        self.assertEqual(0, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_get_key_in_cache(self):
        lc = LRUCache(1)
        lc.put('key', 1)
        out = lc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        lc = LRUCache(1)
        sentinel = object()
        out = lc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        lc = LRUCache(1)
        lc.put('key', 1)
        out = lc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_put_existing_key_in_cache(self):
        lc = LRUCache(1)
        lc.put('key', 1)
        lc.put('key', 2)
        out = lc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, lc.hits)
        self.assertEqual(0, lc.misses)

    def test_key_evicts_when_full(self):
        sentinel = object()
        lc = LRUCache(1)
        lc.put('key1', 1)
        lc.put('key2', 2)
        out1 = lc.get('key1', sentinel)
        out2 = lc.get('key2', sentinel)
        self.assertEqual(sentinel, out1)
        self.assertEqual(2, out2)

    def test_key_evicts_least_recent(self):
        sentinel = object()
        lc = LRUCache(3)
        lc.put('key1', 1)
        lc.put('key2', 2)
        lc.put('key3', 3)
        out1 = lc.get('key2', sentinel)
        out2 = lc.get('key1', sentinel)
        out3 = lc.get('key2', sentinel)

        # key3 should be evicted
        lc.put('key4', 4)
        out4 = lc.get('key1', sentinel)

        # key2 should be evicted
        lc.put('key5', 5)
        out5 = lc.get('key2', sentinel)
        out6 = lc.get('key3', sentinel)
        out7 = lc.get('key4', sentinel)
        out8 = lc.get('key5', sentinel)
        self.assertEqual(2, out1)
        self.assertEqual(1, out2)
        self.assertEqual(2, out3)
        self.assertEqual(1, out4)
        self.assertEqual(sentinel, out5)
        self.assertEqual(sentinel, out6)
        self.assertEqual(4, out7)
        self.assertEqual(5, out8)


class TestMFUCache(unittest.TestCase):

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            MFUCache(0)

    def test_current_size_when_empty(self):
        mc = MFUCache(1)
        self.assertEqual(0, mc.current_size)

    def test_current_size_with_items(self):
        mc = MFUCache(2)
        mc.put('key1', 1)
        mc.put('key2', 2)
        self.assertEqual(2, mc.current_size)

    def test_current_size_with_full_cache(self):
        mc = MFUCache(2)
        mc.put('key1', 1)
        mc.put('key2', 2)
        self.assertEqual(2, mc.current_size)

    def test_max_size(self):
        mc = MFUCache(1)
        self.assertEqual(1, mc.max_size)

    def test_hits_none(self):
        mc = MFUCache(1)
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(0, mc.hits)

    def test_hits_some(self):
        mc = MFUCache(2)
        mc.put('key', object())
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(2, mc.hits)

    def test_misses(self):
        mc = MFUCache(1)
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(2, mc.misses)

    def test_misses_none(self):
        mc = MFUCache(2)
        mc.put('key', object())
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(0, mc.misses)

    def test_clear_with_empty_cache(self):
        mc = MFUCache(1)
        mc.clear()
        self.assertEqual({}, mc._map)
        self.assertEqual(0, len(mc._freq_list))
        self.assertEqual(0, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_clear_with_items(self):
        mc = MFUCache(1)
        mc.put('key1', 1)
        mc.put('key2', 2)
        mc.clear()
        self.assertEqual({}, mc._map)
        self.assertEqual(0, len(mc._freq_list))
        self.assertEqual(0, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_get_key_in_cache(self):
        mc = MFUCache(1)
        mc.put('key', 1)
        out = mc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        mc = MFUCache(1)
        sentinel = object()
        out = mc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        mc = MFUCache(1)
        mc.put('key', 1)
        out = mc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_put_existing_key_in_cache(self):
        mc = MFUCache(1)
        mc.put('key', 1)
        mc.put('key', 2)
        out = mc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_key_evicts_when_full(self):
        sentinel = object()
        mc = MFUCache(1)
        mc.put('key1', 1)
        mc.put('key2', 2)
        out1 = mc.get('key1', sentinel)
        out2 = mc.get('key2', sentinel)
        self.assertEqual(sentinel, out1)
        self.assertEqual(2, out2)

    def test_key_evicts_most_frequent(self):
        sentinel = object()
        mc = MFUCache(2)
        mc.put('key1', 1)
        mc.put('key2', 2)
        out1 = mc.get('key1', sentinel)
        out2 = mc.get('key2', sentinel)
        out3 = mc.get('key2', sentinel)

        # key2 should be evicted
        mc.put('key3', 3)
        out4 = mc.get('key2', sentinel)

        # key1 should be evicted
        mc.put('key4', 4)
        out5 = mc.get('key1', sentinel)
        out6 = mc.get('key3', sentinel)
        out7 = mc.get('key4', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(2, out2)
        self.assertEqual(2, out3)
        self.assertEqual(sentinel, out4)
        self.assertEqual(sentinel, out5)
        self.assertEqual(3, out6)
        self.assertEqual(4, out7)

    def test_key_evicts_random_if_tie(self):
        sentinel = object()
        mc = MFUCache(2)
        mc.put('key1', 1)
        mc.put('key2', 2)
        mc.put('key3', 3)
        out1 = mc.get('key1', sentinel)
        out2 = mc.get('key2', sentinel)
        out3 = mc.get('key3', sentinel)

        self.assertEqual(1, len({1, 2, 3}.difference({out1, out2, out3})))


class TestMQCache(unittest.TestCase):

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            MQCache(0, 1, 1)

    def test_invalid_buffer_size(self):
        with self.assertRaises(ValueError):
            MQCache(1, 0, 1)

    def test_invalid_expire_time(self):
        with self.assertRaises(ValueError):
            MQCache(1, 1, 0)

    def test_invalid_num_queues(self):
        with self.assertRaises(ValueError):
            MQCache(1, 1, 1, 0)

    def test_current_size_when_empty(self):
        mc = MQCache(1, 1, 2)
        self.assertEqual(0, mc.current_size)

    def test_current_size_with_items(self):
        mc = MQCache(1, 1, 2)
        mc.put('key1', 1)
        mc.put('key2', 2)
        self.assertEqual(2, mc.current_size)

    def test_current_size_with_full_cache(self):
        mc = MQCache(1, 1, 2)
        mc.put('key1', 1)
        mc.put('key2', 2)
        mc.put('key3', 3)
        self.assertEqual(2, mc.current_size)

    def test_max_size(self):
        mc = MQCache(4, 3, 2)
        self.assertEqual(7, mc.max_size)

    def test_hits_none(self):
        mc = MQCache(1, 1, 1)
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(0, mc.hits)

    def test_hits_some(self):
        mc = MQCache(1, 1, 1)
        mc.put('key', object())
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(2, mc.hits)

    def test_misses(self):
        mc = MQCache(1, 1, 1)
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(2, mc.misses)

    def test_misses_none(self):
        mc = MQCache(2, 1, 1)
        mc.put('key', object())
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(0, mc.misses)

    def test_clear_with_empty_cache(self):
        mc = MQCache(1, 1, 1)
        mc.clear()
        self.assertEqual({}, mc._map)
        self.assertEqual({}, mc._buffer_map)

        for i in range(mc._num_queues):
            self.assertEqual(0, len(mc._queues[i]))

        self.assertEqual(0, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_clear_with_items(self):
        mc = MQCache(1, 1, 1)
        mc.put('key1', 1)
        mc.put('key2', 2)
        mc.clear()
        self.assertEqual({}, mc._map)
        self.assertEqual({}, mc._buffer_map)

        for i in range(mc._num_queues):
            self.assertEqual(0, len(mc._queues[i]))

        self.assertEqual(0, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_get_key_in_cache(self):
        mc = MQCache(1, 1, 1)
        mc.put('key', 1)
        out = mc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        mc = MQCache(1, 1, 1)
        sentinel = object()
        out = mc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        mc = MQCache(1, 1, 1)
        mc.put('key', 1)
        out = mc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_put_existing_key_in_cache(self):
        mc = MQCache(1, 1, 1)
        mc.put('key', 1)
        mc.put('key', 2)
        out = mc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_key_evicts_when_full(self):
        sentinel = object()
        mc = MQCache(1, 1, 1)
        mc.put('key1', 1)
        mc.put('key2', 2)
        mc.put('key3', 3)
        out1 = mc.get('key1', sentinel)
        out2 = mc.get('key2', sentinel)
        out3 = mc.get('key3', sentinel)
        self.assertEqual(sentinel, out1)
        self.assertEqual(2, out2)
        self.assertEqual(3, out3)

    def test_key_evicts_by_expire_time(self):
        sentinel = object()
        mc = MQCache(2, 1, 1, num_queues=3)
        mc.put('key1', 1)
        mc.put('key2', 2)
        mc.put('key1', 1)
        mc.put('key1', 1)
        mc.put('key1', 1)
        mc.put('key1', 1)
        mc.put('key2', 2)
        mc.put('key2', 2)
        mc.put('key3', 3)
        mc.put('key4', 4)

        out1 = mc.get('key1', sentinel)
        out2 = mc.get('key2', sentinel)
        out3 = mc.get('key3', sentinel)
        out4 = mc.get('key4', sentinel)

        self.assertEqual(out1, sentinel)
        self.assertEqual(out2, 2)
        self.assertEqual(out3, 3)
        self.assertEqual(out4, 4)

    def test_key_evicts_correctly(self):
        sentinel = object()
        mc = MQCache(2, 1, 3, num_queues=1, access_based=False)
        mc.put('key1', 1)
        mc.put('key2', 2)
        mc.put('key3', 3)
        out1 = mc.get('key1', sentinel)
        out2 = mc.get('key2', sentinel)
        out3 = mc.get('key3', sentinel)
        mc.put('key1', 1)

        # key2 should be evicted
        mc.put('key4', 4)
        out4 = mc.get('key2', sentinel)

        # key3 should be evicted
        mc.put('key5', 5)
        out5 = mc.get('key1', sentinel)
        out6 = mc.get('key2', sentinel)
        out7 = mc.get('key3', sentinel)
        out8 = mc.get('key4', sentinel)
        out9 = mc.get('key5', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(2, out2)
        self.assertEqual(3, out3)
        self.assertEqual(sentinel, out4)
        self.assertEqual(1, out5)
        self.assertEqual(sentinel, out6)
        self.assertEqual(sentinel, out7)
        self.assertEqual(4, out8)
        self.assertEqual(5, out9)


class TestMRUCache(unittest.TestCase):

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            MRUCache(0)

    def test_current_size_when_empty(self):
        mc = MRUCache(1)
        self.assertEqual(0, mc.current_size)

    def test_current_size_with_items(self):
        mc = MRUCache(2)
        mc.put('key1', 1)
        mc.put('key2', 2)
        self.assertEqual(2, mc.current_size)

    def test_current_size_with_full_cache(self):
        mc = MRUCache(2)
        mc.put('key1', 1)
        mc.put('key2', 2)
        self.assertEqual(2, mc.current_size)

    def test_max_size(self):
        mc = MRUCache(1)
        self.assertEqual(1, mc.max_size)

    def test_hits_none(self):
        mc = MRUCache(1)
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(0, mc.hits)

    def test_hits_some(self):
        mc = MRUCache(2)
        mc.put('key', object())
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(2, mc.hits)

    def test_misses(self):
        mc = MRUCache(1)
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(2, mc.misses)

    def test_misses_none(self):
        mc = MRUCache(2)
        mc.put('key', object())
        mc.get('key', object())
        mc.get('key', object())
        self.assertEqual(0, mc.misses)

    def test_clear_with_empty_cache(self):
        mc = MRUCache(1)
        mc.clear()
        self.assertEqual({}, mc._map)
        self.assertEqual(0, len(mc._queue))
        self.assertEqual(0, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_clear_with_items(self):
        mc = MRUCache(1)
        mc.put('key1', 1)
        mc.put('key2', 2)
        mc.clear()
        self.assertEqual({}, mc._map)
        self.assertEqual(0, len(mc._queue))
        self.assertEqual(0, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_get_key_in_cache(self):
        mc = MRUCache(1)
        mc.put('key', 1)
        out = mc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        mc = MRUCache(1)
        sentinel = object()
        out = mc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        mc = MRUCache(1)
        mc.put('key', 1)
        out = mc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_put_existing_key_in_cache(self):
        mc = MRUCache(1)
        mc.put('key', 1)
        mc.put('key', 2)
        out = mc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, mc.hits)
        self.assertEqual(0, mc.misses)

    def test_key_evicts_when_full(self):
        sentinel = object()
        mc = MRUCache(1)
        mc.put('key1', 1)
        mc.put('key2', 2)
        out1 = mc.get('key1', sentinel)
        out2 = mc.get('key2', sentinel)
        self.assertEqual(sentinel, out1)
        self.assertEqual(2, out2)

    def test_key_evicts_most_recent(self):
        sentinel = object()
        mc = MRUCache(2)
        mc.put('key1', 1)
        mc.put('key2', 2)
        out1 = mc.get('key1', sentinel)
        out2 = mc.get('key2', sentinel)
        out3 = mc.get('key2', sentinel)

        # key2 should be evicted
        mc.put('key3', 3)
        out4 = mc.get('key1', sentinel)

        # key1 should be evicted
        mc.put('key4', 4)
        out5 = mc.get('key2', sentinel)
        out6 = mc.get('key3', sentinel)
        out7 = mc.get('key4', sentinel)
        out8 = mc.get('key1', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(2, out2)
        self.assertEqual(2, out3)
        self.assertEqual(1, out4)
        self.assertEqual(sentinel, out5)
        self.assertEqual(3, out6)
        self.assertEqual(4, out7)
        self.assertEqual(sentinel, out8)


class TestNMRUCache(unittest.TestCase):

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            NMRUCache(0)

    def test_current_size_when_empty(self):
        nc = NMRUCache(1)
        self.assertEqual(0, nc.current_size)

    def test_current_size_with_items(self):
        nc = NMRUCache(2)
        nc.put('key1', 1)
        nc.put('key2', 2)
        self.assertEqual(2, nc.current_size)

    def test_current_size_with_full_cache(self):
        nc = NMRUCache(2)
        nc.put('key1', 1)
        nc.put('key2', 2)
        self.assertEqual(2, nc.current_size)

    def test_max_size(self):
        nc = NMRUCache(1)
        self.assertEqual(1, nc.max_size)

    def test_hits_none(self):
        nc = NMRUCache(1)
        nc.get('key', object())
        nc.get('key', object())
        self.assertEqual(0, nc.hits)

    def test_hits_some(self):
        nc = NMRUCache(2)
        nc.put('key', object())
        nc.get('key', object())
        nc.get('key', object())
        self.assertEqual(2, nc.hits)

    def test_misses(self):
        nc = NMRUCache(1)
        nc.get('key', object())
        nc.get('key', object())
        self.assertEqual(2, nc.misses)

    def test_misses_none(self):
        nc = NMRUCache(2)
        nc.put('key', object())
        nc.get('key', object())
        nc.get('key', object())
        self.assertEqual(0, nc.misses)

    def test_clear_with_empty_cache(self):
        nc = NMRUCache(1)
        nc.clear()
        self.assertEqual({}, nc._store)
        self.assertEqual(None, nc._mru_item)
        self.assertEqual(0, nc.hits)
        self.assertEqual(0, nc.misses)

    def test_clear_with_items(self):
        nc = NMRUCache(1)
        nc.put('key1', 1)
        nc.put('key2', 2)
        nc.clear()
        self.assertEqual({}, nc._store)
        self.assertEqual(None, nc._mru_item)
        self.assertEqual(0, nc.hits)
        self.assertEqual(0, nc.misses)

    def test_get_key_in_cache(self):
        nc = NMRUCache(1)
        nc.put('key', 1)
        out = nc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        nc = NMRUCache(1)
        sentinel = object()
        out = nc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        nc = NMRUCache(1)
        nc.put('key', 1)
        out = nc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, nc.hits)
        self.assertEqual(0, nc.misses)

    def test_put_existing_key_in_cache(self):
        nc = NMRUCache(1)
        nc.put('key', 1)
        nc.put('key', 2)
        out = nc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, nc.hits)
        self.assertEqual(0, nc.misses)

    def test_key_evicts_when_full(self):
        sentinel = object()
        nc = NMRUCache(1)
        nc.put('key1', 1)
        nc.put('key2', 2)
        out1 = nc.get('key1', sentinel)
        out2 = nc.get('key2', sentinel)
        self.assertEqual(sentinel, out1)
        self.assertEqual(2, out2)

    def test_key_evicts_not_most_recent(self):
        sentinel = object()
        nc = NMRUCache(3)
        nc.put('key1', 1)
        nc.put('key2', 2)
        nc.put('key3', 3)
        out1 = nc.get('key1', sentinel)
        out2 = nc.get('key2', sentinel)
        out3 = nc.get('key2', sentinel)

        # key1 or key3 should be evicted x1
        nc.put('key4', 4)
        nc.get('key3', sentinel)
        nc.put('key4', 4)
        out4 = nc.get('key1', sentinel)
        out5 = nc.get('key3', sentinel)
        out6 = nc.get('key2', sentinel)

        # key1 or key3 or key4 should be evicted x2
        nc.put('key5', 5)
        out7 = nc.get('key1', sentinel)
        out8 = nc.get('key2', sentinel)
        out9 = nc.get('key3', sentinel)
        out10 = nc.get('key4', sentinel)
        out11 = nc.get('key5', sentinel)

        self.assertEqual(1, out1)
        self.assertEqual(2, out2)
        self.assertEqual(2, out3)
        self.assertEqual(1, len({1, 3}.difference({out4, out5})))
        self.assertEqual(2, out6)
        self.assertEqual(2, len({1, 3, 4}.difference({out7, out9, out10})))
        self.assertEqual(2, out8)
        self.assertEqual(5, out11)


class TestRRCache(unittest.TestCase):

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            RRCache(0)

    def test_current_size_when_empty(self):
        rc = RRCache(1)
        self.assertEqual(0, rc.current_size)

    def test_current_size_with_items(self):
        rc = RRCache(2)
        rc.put('key1', 1)
        rc.put('key2', 2)
        self.assertEqual(2, rc.current_size)

    def test_current_size_with_full_cache(self):
        rc = RRCache(2)
        rc.put('key1', 1)
        rc.put('key2', 2)
        self.assertEqual(2, rc.current_size)

    def test_max_size(self):
        rc = RRCache(1)
        self.assertEqual(1, rc.max_size)

    def test_hits_none(self):
        rc = RRCache(1)
        rc.get('key', object())
        rc.get('key', object())
        self.assertEqual(0, rc.hits)

    def test_hits_some(self):
        rc = RRCache(2)
        rc.put('key', object())
        rc.get('key', object())
        rc.get('key', object())
        self.assertEqual(2, rc.hits)

    def test_misses(self):
        rc = RRCache(1)
        rc.get('key', object())
        rc.get('key', object())
        self.assertEqual(2, rc.misses)

    def test_misses_none(self):
        rc = RRCache(2)
        rc.put('key', object())
        rc.get('key', object())
        rc.get('key', object())
        self.assertEqual(0, rc.misses)

    def test_clear_with_empty_cache(self):
        rc = RRCache(1)
        rc.clear()
        self.assertEqual({}, rc._store)
        self.assertEqual(0, rc.hits)
        self.assertEqual(0, rc.misses)

    def test_clear_with_items(self):
        rc = RRCache(1)
        rc.put('key1', 1)
        rc.put('key2', 2)
        rc.clear()
        self.assertEqual({}, rc._store)
        self.assertEqual(0, rc.hits)
        self.assertEqual(0, rc.misses)

    def test_get_key_in_cache(self):
        rc = RRCache(1)
        rc.put('key', 1)
        out = rc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        rc = RRCache(1)
        sentinel = object()
        out = rc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        rc = RRCache(1)
        rc.put('key', 1)
        out = rc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, rc.hits)
        self.assertEqual(0, rc.misses)

    def test_put_existing_key_in_cache(self):
        rc = RRCache(1)
        rc.put('key', 1)
        rc.put('key', 2)
        out = rc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, rc.hits)
        self.assertEqual(0, rc.misses)

    def test_key_evicts_when_full(self):
        sentinel = object()
        rc = RRCache(1)
        rc.put('key1', 1)
        rc.put('key2', 2)
        out1 = rc.get('key1', sentinel)
        out2 = rc.get('key2', sentinel)

        if len({1, 2, sentinel}.difference({out1, out2})) != 1:
            self.fail('Unexpected number of keys in cache!')


class TestSLRUCache(unittest.TestCase):

    def test_invalid_protected_size(self):
        with self.assertRaises(ValueError):
            SLRUCache(0, 1)

    def test_invalid_probationary_size(self):
        with self.assertRaises(ValueError):
            SLRUCache(1, 0)

    def test_current_size_when_empty(self):
        sc = SLRUCache(1, 1)
        self.assertEqual(0, sc.current_size)

    def test_current_size_with_items(self):
        sc = SLRUCache(3, 1)
        sc.put('key1', 1)
        self.assertEqual(1, sc.current_size)

    def test_current_size_with_full_secondary_cache(self):
        sc = SLRUCache(1, 1)
        sc.put('key1', 1)
        sc.put('key2', 2)
        self.assertEqual(1, sc.current_size)

    def test_current_size_with_full_primary_cache(self):
        sc = SLRUCache(1, 1)
        sc.put('key1', 1)
        sc.get('key1', object())
        sc.put('key2', 2)
        sc.get('key2', object())
        self.assertEqual(2, sc.current_size)

    def test_current_size_with_full_secondary_and_primary_cache(self):
        sc = SLRUCache(1, 1)
        sc.put('key1', 1)
        sc.get('key1', object())
        sc.put('key2', 2)
        self.assertEqual(2, sc.current_size)

    def test_max_size(self):
        sc = SLRUCache(4, 3)
        self.assertEqual(7, sc.max_size)

    def test_hits_none(self):
        sc = SLRUCache(1, 1)
        sc.get('key', object())
        sc.get('key', object())
        self.assertEqual(0, sc.hits)

    def test_hits_some(self):
        sc = SLRUCache(1, 1)
        sc.put('key', object())
        sc.get('key', object())
        sc.get('key', object())
        self.assertEqual(2, sc.hits)

    def test_misses(self):
        sc = SLRUCache(1, 1)
        sc.get('key', object())
        sc.get('key', object())
        self.assertEqual(2, sc.misses)

    def test_misses_none(self):
        sc = SLRUCache(2, 1)
        sc.put('key', object())
        sc.get('key', object())
        sc.get('key', object())
        self.assertEqual(0, sc.misses)

    def test_clear_with_empty_cache(self):
        sc = SLRUCache(1, 1)
        sc.clear()
        self.assertEqual({}, sc._protected_map)
        self.assertEqual({}, sc._probationary_map)
        self.assertEqual(0, len(sc._protected_store))
        self.assertEqual(0, len(sc._probationary_store))
        self.assertEqual(0, sc.hits)
        self.assertEqual(0, sc.misses)

    def test_clear_with_items(self):
        sc = SLRUCache(1, 2)
        sc.put('key1', 1)
        sc.put('key2', 2)
        sc.clear()
        self.assertEqual({}, sc._protected_map)
        self.assertEqual({}, sc._probationary_map)
        self.assertEqual(0, len(sc._protected_store))
        self.assertEqual(0, len(sc._probationary_store))
        self.assertEqual(0, sc.hits)
        self.assertEqual(0, sc.misses)

    def test_get_key_in_cache(self):
        sc = SLRUCache(1, 1)
        sc.put('key', 1)
        out = sc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        sc = SLRUCache(1, 1)
        sentinel = object()
        out = sc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        sc = SLRUCache(1, 1)
        sc.put('key', 1)
        out = sc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, sc.hits)
        self.assertEqual(0, sc.misses)

    def test_put_existing_key_in_cache(self):
        sc = SLRUCache(1, 1)
        sc.put('key', 1)
        sc.put('key', 2)
        out = sc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, sc.hits)
        self.assertEqual(0, sc.misses)

    def test_key_evicts_when_probationary_full(self):
        sentinel = object()
        sc = SLRUCache(1, 1)
        sc.put('key1', 1)
        sc.put('key2', 2)
        out1 = sc.get('key1', sentinel)
        out2 = sc.get('key2', sentinel)
        self.assertEqual(sentinel, out1)
        self.assertEqual(2, out2)

    def test_key_moves_to_probationary_when_protected_full(self):
        sentinel = object()
        sc = SLRUCache(1, 1)
        sc.put('key1', 1)
        out1 = sc.get('key1', sentinel)
        sc.put('key2', 2)
        out2 = sc.get('key2', sentinel)
        out3 = sc.get('key1', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(2, out2)
        self.assertEqual(1, out3)

    def test_key_evicts_when_full(self):
        sentinel = object()
        sc = SLRUCache(1, 2)
        sc.put('key1', 1)
        sc.put('key2', 2)
        out1 = sc.get('key1', sentinel)
        out2 = sc.get('key2', sentinel)
        sc.put('key2', 2)
        sc.put('key1', 1)
        sc.put('key3', 3)

        # Key1 in protected, Key2 & Key3 in probationary
        out3 = sc.get('key1', sentinel)
        out4 = sc.get('key2', sentinel)
        sc.put('key4', 4)

        # Key2 in protected, Key1 & Key 3 in probationary
        out5 = sc.get('key1', sentinel)
        out6 = sc.get('key2', sentinel)
        out7 = sc.get('key3', sentinel)
        out8 = sc.get('key4', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(2, out2)
        self.assertEqual(1, out3)
        self.assertEqual(2, out4)
        self.assertEqual(1, out5)
        self.assertEqual(2, out6)
        self.assertEqual(sentinel, out7)
        self.assertEqual(4, out8)


class TestStaticCache(unittest.TestCase):

    def test_current_size_when_empty(self):
        sc = StaticCache()
        self.assertEqual(0, sc.current_size)

    def test_current_size_with_items(self):
        sc = StaticCache()
        sc.put('key1', 1)
        sc.put('key2', 2)
        self.assertEqual(2, sc.current_size)

    def test_max_size(self):
        sc = StaticCache()
        self.assertEqual(float('inf'), sc.max_size)

    def test_hits_none(self):
        sc = StaticCache()
        sc.get('key', object())
        sc.get('key', object())
        self.assertEqual(0, sc.hits)

    def test_hits_some(self):
        sc = StaticCache()
        sc.put('key', 1)
        sc.get('key', object())
        sc.get('key', object())
        self.assertEqual(2, sc.hits)

    def test_misses(self):
        sc = StaticCache()
        sc.get('key', object())
        sc.get('key', object())
        self.assertEqual(2, sc.misses)

    def test_misses_none(self):
        sc = StaticCache()
        sc.put('key', 1)
        sc.get('key', object())
        sc.get('key', object())
        self.assertEqual(0, sc.misses)

    def test_clear_with_empty_cache(self):
        sc = StaticCache()
        sc.clear()
        self.assertEqual({}, sc._store)
        self.assertEqual(0, sc.hits)
        self.assertEqual(0, sc.misses)

    def test_clear_with_items(self):
        sc = StaticCache()
        sc.put('key1', 1)
        sc.put('key2', 2)
        sc.clear()
        self.assertEqual({}, sc._store)
        self.assertEqual(0, sc.hits)
        self.assertEqual(0, sc.misses)

    def test_get_key_in_cache(self):
        sc = StaticCache()
        sc.put('key', 1)
        out = sc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        sentinel = object()
        sc = StaticCache()
        out = sc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        sc = StaticCache()
        sc.put('key', 1)
        out = sc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, sc.hits)
        self.assertEqual(0, sc.misses)

    def test_put_existing_key_in_cache(self):
        sc = StaticCache()
        sc.put('key', 1)
        sc.put('key', 2)
        out = sc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, sc.hits)
        self.assertEqual(0, sc.misses)


class TestTLRUCache(unittest.TestCase):

    def test_invalid_expire_time(self):
        with self.assertRaises(ValueError):
            TLRUCache(0)

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            TLRUCache(1, 0)

    def test_current_size_when_empty(self):
        tc = TLRUCache(1)
        self.assertEqual(0, tc.current_size)

    def test_current_size_with_items(self):
        tc = TLRUCache(2)
        tc.put('key1', 1)
        tc.put('key2', 2)
        self.assertEqual(2, tc.current_size)

    def test_current_size_with_full_cache(self):
        tc = TLRUCache(2, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        self.assertEqual(1, tc.current_size)

    def test_max_size_with_size(self):
        tc = TLRUCache(1, 1)
        self.assertEqual(1, tc.max_size)

    def test_max_size_without_size(self):
        tc = TLRUCache(1)
        self.assertEqual(float('inf'), tc.max_size)

    def test_hits_none(self):
        tc = TLRUCache(1)
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(0, tc.hits)

    def test_hits_some(self):
        tc = TLRUCache(2)
        tc.put('key', object())
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(2, tc.hits)

    def test_misses(self):
        tc = TLRUCache(1)
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(2, tc.misses)

    def test_misses_none(self):
        tc = TLRUCache(2)
        tc.put('key', object())
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(0, tc.misses)

    def test_clear_with_empty_cache(self):
        tc = TLRUCache(1, 2)
        tc.clear()
        self.assertEqual({}, tc._map)
        self.assertEqual(0, tc._queue.size)
        self.assertEqual(0, tc._access_queue.size)
        self.assertEqual(0, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_clear_with_items(self):
        tc = TLRUCache(1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        tc.clear()
        self.assertEqual({}, tc._map)
        self.assertEqual(0, tc._access_queue.size)
        self.assertEqual(0, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_get_key_in_cache(self):
        tc = TLRUCache(1)
        tc.put('key', 1)
        out = tc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        tc = TLRUCache(1)
        sentinel = object()
        out = tc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        tc = TLRUCache(1)
        tc.put('key', 1)
        out = tc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_put_existing_key_in_cache(self):
        tc = TLRUCache(1)
        tc.put('key', 1)
        tc.put('key', 2)
        out = tc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_key_evicts_by_access(self):
        sentinel = object()
        tc = TLRUCache(2, 3, access_based=True)
        tc.put('key1', 1)
        out1 = tc.get('key1', sentinel)
        out2 = tc.get('key2', sentinel)
        out3 = tc.get('key2', sentinel)
        out4 = tc.get('key1', sentinel)
        out5 = tc.get('key1', sentinel)
        out6 = tc.get('key1', sentinel)
        out7 = tc.get('key1', sentinel)
        out8 = tc.get('key2', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(sentinel, out2)
        self.assertEqual(sentinel, out3)
        self.assertEqual(sentinel, out4)
        self.assertEqual(sentinel, out5)
        self.assertEqual(sentinel, out6)
        self.assertEqual(sentinel, out7)
        self.assertEqual(sentinel, out8)

    def test_key_evicts_by_access_no_reset(self):
        sentinel = object()
        tc = TLRUCache(2, reset_on_access=False, access_based=True)
        tc.put('key1', 1)
        tc.put('key1', 1)
        out1 = tc.get('key1', sentinel)
        out2 = tc.get('key2', sentinel)
        out3 = tc.get('key2', sentinel)
        out4 = tc.get('key1', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(sentinel, out2)
        self.assertEqual(sentinel, out3)
        self.assertEqual(sentinel, out4)

    def test_key_no_expire_on_reaccess(self):
        sentinel = object()
        tc = TLRUCache(1)
        tc.put('key1', 1)
        out1 = tc.get('key1', sentinel)
        out2 = tc.get('key1', sentinel)
        out3 = tc.get('key1', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(1, out2)
        self.assertEqual(1, out3)

    def test_key_evicts_by_size(self):
        sentinel = object()
        tc = TLRUCache(3, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        tc.put('key2', 2)
        out1 = tc.get('key1', sentinel)
        out2 = tc.get('key2', sentinel)
        self.assertEqual(sentinel, out1)
        self.assertEqual(2, out2)


class TestTwoQCache(unittest.TestCase):

    def test_invalid_primary_size(self):
        with self.assertRaises(ValueError):
            TwoQCache(0, 1)

    def test_invalid_secondary_size(self):
        with self.assertRaises(ValueError):
            TwoQCache(1, 0)

    def test_current_size_when_empty(self):
        tc = TwoQCache(1, 1)
        self.assertEqual(0, tc.current_size)

    def test_current_size_with_items(self):
        tc = TwoQCache(3, 1)
        tc.put('key1', 1)
        self.assertEqual(1, tc.current_size)

    def test_current_size_with_full_secondary_cache(self):
        tc = TwoQCache(1, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        self.assertEqual(1, tc.current_size)

    def test_current_size_with_full_primary_cache(self):
        tc = TwoQCache(1, 1)
        tc.put('key1', 1)
        tc.get('key1', object())
        tc.put('key2', 2)
        tc.get('key2', object())
        self.assertEqual(1, tc.current_size)

    def test_current_size_with_full_secondary_and_primary_cache(self):
        tc = TwoQCache(1, 1)
        tc.put('key1', 1)
        tc.get('key1', object())
        tc.put('key2', 2)
        self.assertEqual(2, tc.current_size)

    def test_max_size(self):
        tc = TwoQCache(4, 3)
        self.assertEqual(7, tc.max_size)

    def test_hits_none(self):
        tc = TwoQCache(1, 1)
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(0, tc.hits)

    def test_hits_some(self):
        tc = TwoQCache(1, 1)
        tc.put('key', object())
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(2, tc.hits)

    def test_misses(self):
        tc = TwoQCache(1, 1)
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(2, tc.misses)

    def test_misses_none(self):
        tc = TwoQCache(2, 1)
        tc.put('key', object())
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(0, tc.misses)

    def test_clear_with_empty_cache(self):
        tc = TwoQCache(1, 1)
        tc.clear()
        self.assertEqual({}, tc._primary_map)
        self.assertEqual({}, tc._secondary_map)
        self.assertEqual(0, len(tc._primary_store))
        self.assertEqual(0, len(tc._secondary_store))
        self.assertEqual(0, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_clear_with_items(self):
        tc = TwoQCache(1, 2)
        tc.put('key1', 1)
        tc.put('key2', 2)
        tc.clear()
        self.assertEqual({}, tc._primary_map)
        self.assertEqual({}, tc._secondary_map)
        self.assertEqual(0, len(tc._primary_store))
        self.assertEqual(0, len(tc._secondary_store))
        self.assertEqual(0, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_get_key_in_cache(self):
        tc = TwoQCache(1, 1)
        tc.put('key', 1)
        out = tc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        tc = TwoQCache(1, 1)
        sentinel = object()
        out = tc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        tc = TwoQCache(1, 1)
        tc.put('key', 1)
        out = tc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_put_existing_key_in_cache(self):
        tc = TwoQCache(1, 1)
        tc.put('key', 1)
        tc.put('key', 2)
        out = tc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_key_evicts_when_secondary_full(self):
        sentinel = object()
        tc = TwoQCache(1, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        out1 = tc.get('key1', sentinel)
        out2 = tc.get('key2', sentinel)
        self.assertEqual(sentinel, out1)
        self.assertEqual(2, out2)

    def test_key_evicts_when_primary_full(self):
        sentinel = object()
        tc = TwoQCache(1, 1)
        tc.put('key1', 1)
        out1 = tc.get('key1', sentinel)
        tc.put('key1', 1)
        tc.put('key2', 2)
        out2 = tc.get('key2', sentinel)
        out3 = tc.get('key1', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(2, out2)
        self.assertEqual(sentinel, out3)


class TestTwoQFullCache(unittest.TestCase):

    def test_invalid_primary_size(self):
        with self.assertRaises(ValueError):
            TwoQFullCache(0, 1, 1)

    def test_invalid_secondary_in_size(self):
        with self.assertRaises(ValueError):
            TwoQFullCache(1, 0, 1)

    def test_invalid_secondary_out_size(self):
        with self.assertRaises(ValueError):
            TwoQFullCache(1, 1, 0)

    def test_current_size_when_empty(self):
        tc = TwoQFullCache(1, 1, 1)
        self.assertEqual(0, tc.current_size)

    def test_current_size_with_items(self):
        tc = TwoQFullCache(3, 1, 1)
        tc.put('key1', 1)
        self.assertEqual(1, tc.current_size)

    def test_current_size_with_full_secondary_in_cache(self):
        tc = TwoQFullCache(1, 2, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        self.assertEqual(2, tc.current_size)

    def test_current_size_with_full_secondary_out_cache(self):
        tc = TwoQFullCache(1, 1, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        self.assertEqual(2, tc.current_size)

    def test_current_size_with_full_primary_cache(self):
        tc = TwoQFullCache(1, 1, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        tc.get('key1', object())
        tc.put('key3', 3)
        tc.get('key2', object())
        self.assertEqual(2, tc.current_size)

    def test_current_size_with_all_full_caches(self):
        tc = TwoQFullCache(1, 1, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        tc.get('key1', object())
        tc.put('key3', 3)
        self.assertEqual(3, tc.current_size)

    def test_max_size(self):
        tc = TwoQFullCache(4, 3, 1)
        self.assertEqual(8, tc.max_size)

    def test_hits_none(self):
        tc = TwoQFullCache(1, 1, 1)
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(0, tc.hits)

    def test_hits_some(self):
        tc = TwoQFullCache(1, 1, 1)
        tc.put('key', object())
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(2, tc.hits)

    def test_misses(self):
        tc = TwoQFullCache(1, 1, 1)
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(2, tc.misses)

    def test_misses_none(self):
        tc = TwoQFullCache(2, 1, 1)
        tc.put('key', object())
        tc.get('key', object())
        tc.get('key', object())
        self.assertEqual(0, tc.misses)

    def test_clear_with_empty_cache(self):
        tc = TwoQFullCache(1, 1, 1)
        tc.clear()
        self.assertEqual({}, tc._primary_map)
        self.assertEqual({}, tc._secondary_in_map)
        self.assertEqual({}, tc._secondary_out_map)
        self.assertEqual(0, len(tc._primary_store))
        self.assertEqual(0, len(tc._secondary_in_store))
        self.assertEqual(0, len(tc._secondary_out_store))
        self.assertEqual(0, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_clear_with_items(self):
        tc = TwoQFullCache(1, 2, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        tc.clear()
        self.assertEqual({}, tc._primary_map)
        self.assertEqual({}, tc._secondary_in_map)
        self.assertEqual({}, tc._secondary_out_map)
        self.assertEqual(0, len(tc._primary_store))
        self.assertEqual(0, len(tc._secondary_in_store))
        self.assertEqual(0, len(tc._secondary_out_store))
        self.assertEqual(0, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_get_key_in_cache(self):
        tc = TwoQFullCache(1, 1, 1)
        tc.put('key', 1)
        out = tc.get('key', object())
        self.assertEqual(1, out)

    def test_get_key_not_in_cache(self):
        tc = TwoQFullCache(1, 1, 1)
        sentinel = object()
        out = tc.get('key', sentinel)
        self.assertEqual(sentinel, out)

    def test_put_key_in_cache(self):
        tc = TwoQFullCache(1, 1, 1)
        tc.put('key', 1)
        out = tc.get('key', object())
        self.assertEqual(1, out)
        self.assertEqual(1, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_put_existing_key_in_cache(self):
        tc = TwoQFullCache(1, 1, 1)
        tc.put('key', 1)
        tc.put('key', 2)
        out = tc.get('key', object())
        self.assertEqual(2, out)
        self.assertEqual(1, tc.hits)
        self.assertEqual(0, tc.misses)

    def test_key_evicts_when_secondary_full(self):
        sentinel = object()
        tc = TwoQFullCache(1, 1, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        tc.put('key3', 3)
        out1 = tc.get('key1', sentinel)
        out2 = tc.get('key2', sentinel)
        out3 = tc.get('key3', sentinel)
        self.assertEqual(sentinel, out1)
        self.assertEqual(2, out2)
        self.assertEqual(3, out3)

    def test_key_evicts_when_primary_full(self):
        sentinel = object()
        tc = TwoQFullCache(1, 1, 1)
        tc.put('key1', 1)
        tc.put('key2', 2)
        out1 = tc.get('key1', sentinel)
        tc.put('key3', 3)
        out2 = tc.get('key2', sentinel)
        out3 = tc.get('key1', sentinel)
        out4 = tc.get('key3', sentinel)
        self.assertEqual(1, out1)
        self.assertEqual(2, out2)
        self.assertEqual(sentinel, out3)
        self.assertEqual(3, out4)

    def test_key_evicts_correctly(self):
        sentinel = object()
        tc = TwoQFullCache(1, 1, 1)
        tc.put('key1', 1)
        out1 = tc.get('key1', sentinel)
        out2 = tc.get('key1', sentinel)
        tc.put('key1', 1)
        tc.put('key2', 2)
        tc.put('key1', 1)
        tc.put('key1', 1)
        tc.put('key3', 3)
        tc.put('key2', 2)
        out3 = tc.get('key1', sentinel)
        out4 = tc.get('key2', sentinel)
        out5 = tc.get('key3', sentinel)
        tc.put('key4', 4)
        out6 = tc.get('key1', sentinel)
        out7 = tc.get('key2', sentinel)
        out8 = tc.get('key3', sentinel)
        out9 = tc.get('key4', sentinel)
        self.assertEqual(out1, 1)
        self.assertEqual(out2, 1)
        self.assertEqual(out3, sentinel)
        self.assertEqual(out4, 2)
        self.assertEqual(out5, 3)
        self.assertEqual(out6, sentinel)
        self.assertEqual(out7, 2)
        self.assertEqual(out8, 3)
        self.assertEqual(out9, 4)


if __name__ == '__main__':
    unittest.main()
