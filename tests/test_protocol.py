"""Test protocol module"""
import json

import pytest

from common.protocol import pack, MAGIC, HEADER


def test_pack():
    """Test pack function"""
    test_obj = {"test": "data", "number": 42}

    # Pack the object
    packed = pack(test_obj)

    # Check header
    assert len(packed) >= HEADER.size
    magic, length = HEADER.unpack(packed[:HEADER.size])
    assert magic == MAGIC

    # Check payload
    payload = packed[HEADER.size:]
    assert len(payload) == length
    unpacked = json.loads(payload.decode('utf-8'))
    assert unpacked == test_obj


def test_pack_empty_dict():
    """Test pack with empty dict"""
    test_obj = {}
    packed = pack(test_obj)

    magic, length = HEADER.unpack(packed[:HEADER.size])
    assert magic == MAGIC
    assert length == 2  # "{}" is 2 bytes