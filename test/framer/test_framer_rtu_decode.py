"""Unit‑tests that focus on **FramerRTU.decode()** using the *real* `DecodePDU` implementation.

Save as **test_framer_rtu_decode.py** next to the existing big framer test module.
The tests run fast and do **not** depend on any dummy decoder classes.
"""

from __future__ import annotations

import pytest

from amodbus.framer import FramerRTU
from amodbus.pdu import DecodePDU

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture(name="framer")
def _framer_fixture() -> FramerRTU:
    """Return a *client‑side* RTU framer with the real decoder attached."""

    return FramerRTU(DecodePDU(is_server=False))


def _make_frame(framer: FramerRTU, device_id: int, pdu: bytes) -> bytes:
    """Helper – use the framer's *encode* to build a CRC‑correct frame."""

    return framer.encode(pdu, device_id, 0)

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_fixed_length_success(framer: FramerRTU):
    """Write‑Single‑Register response (function 0x06, 8‑byte frame)."""

    pdu = b"\x06\x00\x01\x00\x02"  # func + register + value
    frame = _make_frame(framer, 0x01, pdu)

    used, dev, tid, decoded = framer.decode(frame)

    assert used == len(frame)
    assert dev == 0x01
    assert tid == 0
    assert decoded == pdu


def test_variable_length_success(framer: FramerRTU):
    """Read‑Holding‑Registers **response** (function 0x03, byte‑count = 4)."""

    pdu = b"\x03\x04\x00\x10\x00\x11"  # func + BC + 2 registers
    frame = _make_frame(framer, 0x01, pdu)

    used, dev, _, decoded = framer.decode(frame)

    assert used == len(frame)
    assert dev == 0x01
    assert decoded == pdu


def test_garbage_then_frame(framer: FramerRTU):
    """0xFF junk followed by a good frame – junk must be skipped."""

    garbage = b"\xFF\xFF\x11\x22"
    pdu = b"\x06\x00\x05\x00\x06"
    good = _make_frame(framer, 0x10, pdu)
    stream = garbage + good

    used, dev, _, decoded = framer.decode(stream)

    assert used == len(stream)
    assert dev == 0x10
    assert decoded == pdu


def test_bad_crc_rejected(framer: FramerRTU):
    """Frame with an invalid CRC – decoder must not consume bytes."""

    pdu = b"\x06\x00\x01\x00\x02"
    frame = bytearray(_make_frame(framer, 0x01, pdu))
    frame[-1] ^= 0xFF  # corrupt CRC

    used, dev, tid, decoded = framer.decode(bytes(frame))

    assert used == 0
    assert dev == 0
    assert tid == 0
    assert decoded == framer.EMPTY


def test_incomplete_frame_waits(framer: FramerRTU):
    """Provide only half a frame; decoder must return used==0 (need more)."""

    full = _make_frame(framer, 0x01, b"\x06\x00\x01\x00\x02")
    partial = full[:4]  # addr + func + reg‑hi + reg‑lo

    used, _, _, decoded = framer.decode(partial)

    assert used == 0
    assert decoded == framer.EMPTY
