"""Test utilities."""

import struct

import pytest

from amodbus.utilities import dict_property, pack_bitstring, unpack_bitstring

_test_master = {4: "d"}


class DictPropertyTester:  # pylint: disable=too-few-public-methods
    """Dictionary property test."""

    def __init__(self):
        """Initialize."""
        self.test = {1: "a"}
        self._test = {2: "b"}
        self.__test = {3: "c"}  # pylint: disable=unused-private-member

    l_1 = dict_property(lambda s: s.test, 1)
    l_2 = dict_property(lambda s: s._test, 2)  # pylint: disable=protected-access
    l_3 = dict_property(lambda s: s.__test, 3)  # pylint: disable=protected-access
    s_1 = dict_property("test", 1)
    s_2 = dict_property("_test", 2)
    g_1 = dict_property(_test_master, 4)


class TestUtility:
    """Unittest for the pymod.utilities module."""

    def setup_method(self):
        """Initialize the test environment."""
        self.data = struct.pack(  # pylint: disable=attribute-defined-outside-init
            ">HHHH", 0x1234, 0x2345, 0x3456, 0x4567
        )
        self.string = b"test the computation"  # pylint: disable=attribute-defined-outside-init

    def teardown_method(self):
        """Clean up the test environment."""

    def test_dict_property(self):
        """Test all string <=> bit packing functions."""
        result = DictPropertyTester()
        assert result.l_1 == "a"
        assert result.l_2 == "b"
        assert result.l_3 == "c"
        assert result.s_1 == "a"
        assert result.s_2 == "b"
        assert result.g_1 == "d"

        for store in "l_1 l_2 l_3 s_1 s_2 g_1".split(" "):
            setattr(result, store, "x")

        assert result.l_1 == "x"
        assert result.l_2 == "x"
        assert result.l_3 == "x"
        assert result.s_1 == "x"
        assert result.s_2 == "x"
        assert result.g_1 == "x"

    @pytest.mark.parametrize(
        ("bytestream", "bitlist"),
        [
            (b"\x55", [True, False, True, False, True, False, True, False]),
            (b"\x80", [False] * 7 + [True]),
            (b"\x01", [True] + [False] * 7),
            (b"\x80\x00", [False] * 7 + [True] + [False] * 8),
            (b"\x01\x00", [True] + [False] * 15),
        ],
    )
    def test_bit_packing(self, bytestream, bitlist):
        """Test all string <=> bit packing functions."""
        assert pack_bitstring(bitlist) == bytestream
        assert unpack_bitstring(bytestream) == bitlist
