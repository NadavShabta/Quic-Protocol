from unittest import TestCase
from quic.var_int import VarInt


class TestVarInt(TestCase):
    def test_init(self):
        t = VarInt(0x3fffffff)
        assert t.length == 8
        t = VarInt(0x3fffffff - 1)
        assert t.length == 4

    def test_to_bytes(self):
        t = VarInt(0xfe8a9bfc)
        expected = b'\xc0\x00\x00\x00\xfe\x8a\x9b\xfc'
        assert VarInt.to_bytes(t) == expected

    def test_length_to_format(self):
        assert VarInt.length_to_format(2) == "H"

    def test_format(self):
        t = VarInt(0xfe8a9bfc)
        assert t.length_to_format(t.length) == "Q"

    def test_length_of(self):
        t = VarInt(0xfe8a9bfc)
        expected = 4
        actual = VarInt.length_of(t.value).value
        assert actual == expected
