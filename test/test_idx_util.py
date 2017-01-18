#!/usr/bin/env python

import logging
import unittest
import shutil
import struct
from sosdb import Sos as sos

logger = logging.getLogger(__name__)


def obj2tuple(obj):
    if not obj:
        return None
    return tuple(obj[i] for i in range(0, obj.get_schema().attr_count()))

HALF = 5
REPEAT = 2

def attr_key_half_next_INT32(a, v):
    k = sos.Key(attr=a)
    k.set_value(v + HALF)
    return k

def attr_key_half_prev_INT32(a, v):
    k = sos.Key(attr=a)
    k.set_value(v - HALF)
    return k

def attr_key_half_next_STRUCT(a, v):
    (i,j,k,l) = struct.unpack("!LLLL", v)
    assert(i == j == k == l)
    k = sos.Key(attr=a)
    ii = i + HALF
    _v = struct.pack("!LLLL", ii, ii, ii, ii)
    k.set_value(_v)
    return k

def attr_key_half_prev_STRUCT(a, v):
    (i,j,k,l) = struct.unpack("!LLLL", v)
    assert(i == j == k == l)
    k = sos.Key(attr=a)
    ii = i - HALF
    _v = struct.pack("!LLLL", ii, ii, ii, ii)
    k.set_value(_v)
    return k

class SosIterWrap(object):
    def __init__(self, itr, rev = False):
        self.itr = itr
        self.rev = rev

    def __iter__(self):
        b = True
        while b:
            yield self.itr.item()
            b = self.itr.next() if not self.rev else self.itr.prev()


class TestIndexBase(object):
    """
    This is an abstract base class of SOS4 index test.
    """
    @classmethod
    def setUpClass(cls):
        # purge existing store
        shutil.rmtree(cls.STORE_PATH, ignore_errors=True)

        # create new store
        cls.cont = cont = sos.Container()
        cont.create(cls.STORE_PATH)
        cont.open(cls.STORE_PATH)

        # new partition
        cont.part_create(cls.PART_NAME)
        cls.part = part = cont.part_by_name(cls.PART_NAME)
        part.state_set("PRIMARY")

        # new schema
        cls.schema = schema = sos.Schema()
        schema.from_template(cls.SCHEMA_NAME, [
                    {
                        "name": "i32",
                        "type": "INT32",
                        "index": {
                            "type": cls.IDX_TYPE,
                            "key": "INT32",
                            "args": cls.IDX_ARG,
                        }
                    },
                    {
                        # {uint32, uint32, uint64}
                        "name": "struct",
                        "type": "STRUCT",
                        "size": 16,
                        "index": {
                            "type": cls.IDX_TYPE,
                            "key": "MEMCMP",
                            "args": cls.IDX_ARG,
                        }
                    },
                ])

        cls.attr_key_half_next = [
            attr_key_half_next_INT32,
            attr_key_half_next_STRUCT,
        ]
        cls.attr_key_half_prev = [
            attr_key_half_prev_INT32,
            attr_key_half_prev_STRUCT,
        ]

        schema.add(cont)

        cls.input_data = [ (i, struct.pack("!LLLL", i, i, i, i)) \
                                    for i in range(10, 500, 10) \
                                            for _ in range(REPEAT) ]
        # data
        for d in cls.input_data:
            obj = schema.alloc()
            obj[:] = d
            obj.index_add()

    @classmethod
    def tearDownClass(cls):
        cls.cont.close()

    def getContainer(self):
        return self.cont

    def test_iter(self):
        for attr in self.schema:
            itr = sos.AttrIter(attr)
            data = []
            b = itr.begin()
            while b:
                obj = itr.item()
                t = obj2tuple(obj)
                data.append(t)
                b = itr.next()
            self.assertEqual(data, self.input_data)

    def test_iter_rev(self):
        for attr in self.schema:
            itr = sos.AttrIter(attr)
            data = []
            b = itr.end()
            while b:
                obj = itr.item()
                t = obj2tuple(obj)
                data.append(t)
                b = itr.prev()
            data.reverse()
            self.assertEqual(data, self.input_data)

    def test_iter_fwd_rev(self):
        for attr in self.schema:
            itr = sos.AttrIter(attr)
            data_fwd = []
            itr.begin()
            for i in range(0, 10):
                data_fwd.append(obj2tuple(itr.item()))
                itr.next()
            data_rev = []
            itr.prev()
            for i in range(0, 10):
                data_rev.append(obj2tuple(itr.item()))
                itr.prev()
            data_rev.reverse()
            self.assertEqual(data_fwd, data_rev)

    def test_iter_inf(self):
        for attr in self.schema:
            aid = attr.attr_id()
            itr = sos.AttrIter(attr)
            for idx in range(0, len(self.input_data), REPEAT):
                data = self.input_data[idx]
                key = self.attr_key_half_next[aid](attr, data[aid])
                itr.prop_set("inf_last_dup", 1)
                self.assertTrue(itr.find_inf(key))
                obj = itr.item()
                self.assertEqual(obj2tuple(obj)[aid], data[aid])
                self.assertEqual(obj2tuple(obj), data)
                l0 = [obj2tuple(obj) for obj in SosIterWrap(itr, rev=True)]
                l0.reverse()
                l1 = self.input_data[:(idx+REPEAT)]
                self.assertEqual(l0, l1)

    def test_iter_inf_exact(self):
        for attr in self.schema:
            aid = attr.attr_id()
            itr = sos.AttrIter(attr)
            for data in self.input_data:
                key = sos.Key(attr=attr)
                key.set_value(data[aid])
                self.assertTrue(itr.find_inf(key))
                obj = itr.item()
                self.assertEqual(obj2tuple(obj), data,
                                    msg="bad result attr: %s"%attr.name())

    def test_iter_sup(self):
        for attr in self.schema:
            aid = attr.attr_id()
            itr = sos.AttrIter(attr)
            for idx in range(0, len(self.input_data), REPEAT):
                data = self.input_data[idx]
                key = self.attr_key_half_prev[aid](attr, data[aid])
                self.assertTrue(itr.find_sup(key))
                obj = itr.item()
                self.assertEqual(obj2tuple(obj)[aid], data[aid])
                self.assertEqual(obj2tuple(obj), data)
                l0 = [obj2tuple(obj) for obj in SosIterWrap(itr)]
                l1 = self.input_data[idx:]
                self.assertEqual(l0, l1)

    def test_iter_sup_exact(self):
        for attr in self.schema:
            aid = attr.attr_id()
            itr = sos.AttrIter(attr)
            for data in self.input_data:
                key = sos.Key(attr=attr)
                key.set_value(data[aid])
                self.assertTrue(itr.find_sup(key))
                obj = itr.item()
                t = obj2tuple(obj)
                self.assertEqual(obj2tuple(obj), data,
                                    msg="bad result attr: %s"%attr.name())

    def test_iter_last(self):
        for attr in self.schema:
            itr = sos.AttrIter(attr)
            self.assertTrue(itr.end())
            obj = itr.item()
            self.assertEqual(obj2tuple(obj),self.input_data[len(self.input_data)-1])

    def test_iter_begin(self):
        for attr in self.schema:
            itr = sos.AttrIter(attr)
            self.assertTrue(itr.begin())
            self.assertEqual(obj2tuple(itr.item()),self.input_data[0])

    def test_iter_pos(self):
        for attr in self.schema:
            itr = sos.AttrIter(attr)
            self.assertTrue(itr.begin())
            self.assertTrue(itr.next())
            self.assertTrue(itr.next())
            obj = itr.item()
            pos = itr.get_pos()
            self.assertIsNotNone(obj)

            itr2 = sos.AttrIter(attr)
            rc = itr2.set_pos(pos)
            self.assertEqual(rc, 0)
            obj2 = itr2.item()
            self.assertIsNotNone(obj2)
            self.assertEqual(obj[:], obj2[:])
