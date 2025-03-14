"""Modbus Utilities.

A collection of utilities for packing data, unpacking
data computing checksums, and decode checksums.
"""

from __future__ import annotations

# pylint: disable=missing-type-doc
import struct


def dict_property(store, index):
    """Create class properties from a dictionary.

    Basically this allows you to remove a lot of possible
    boilerplate code.

    :param store: The store store to pull from
    :param index: The index into the store to close over
    :returns: An initialized property set
    """
    if hasattr(store, "__call__"):
        getter = lambda self: store(self)[index]  # pylint: disable=unnecessary-lambda-assignment
        setter = lambda self, value: store(self).__setitem__(  # pylint: disable=unnecessary-lambda-assignment
            index, value
        )
    elif isinstance(store, str):
        getter = (
            lambda self: self.__getattribute__(  # pylint: disable=unnecessary-dunder-call,unnecessary-lambda-assignment
                store
            )[index]
        )
        setter = lambda self, value: self.__getattribute__(  # pylint: disable=unnecessary-dunder-call,unnecessary-lambda-assignment
            store
        ).__setitem__(
            index, value
        )
    else:
        getter = lambda self: store[index]  # pylint: disable=unnecessary-lambda-assignment
        setter = lambda self, value: store.__setitem__(index, value)  # pylint: disable=unnecessary-lambda-assignment

    return property(getter, setter)


# --------------------------------------------------------------------------- #
# Bit packing functions
# --------------------------------------------------------------------------- #
def pack_bitstring(bits: list[bool]) -> bytes:
    """Create a bytestring out of a list of bits.

    :param bits: A list of bits

    example::

        bits   = [False, True, False, True]
        result = pack_bitstring(bits)
    """
    ret = b""
    i = packed = 0
    for bit in bits:
        if bit:
            packed += 128
        i += 1
        if i == 8:
            ret += struct.pack(">B", packed)
            i = packed = 0
        else:
            packed >>= 1
    if 0 < i < 8:
        packed >>= 7 - i
        ret += struct.pack(">B", packed)
    return ret


def unpack_bitstring(data: bytes) -> list[bool]:
    """Create bit list out of a bytestring.

    :param data: The modbus data packet to decode

    example::

        bytes  = "bytes to decode"
        result = unpack_bitstring(bytes)
    """
    byte_count = len(data)
    bits = []
    for byte in range(byte_count):
        value = int(data[byte])
        for _ in range(8):
            bits.append((value & 1) == 1)
            value >>= 1
    return bits


# --------------------------------------------------------------------------- #
# Error Detection Functions
# --------------------------------------------------------------------------- #


def hexlify_packets(packet):
    """Return hex representation of bytestring received.

    :param packet:
    :return:
    """
    if not packet:
        return ""
    return " ".join([hex(int(x)) for x in packet])
