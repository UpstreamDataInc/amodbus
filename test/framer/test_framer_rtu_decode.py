"""RTU framing tests using the real PDU decoder."""

from __future__ import annotations

import pytest

from amodbus.framer import FramerRTU
from amodbus.pdu import DecodePDU
from amodbus.pdu.diag_message import (
    GetClearModbusPlusResponse,
    ReturnQueryDataRequest,
    ReturnQueryDataResponse,
)


@pytest.fixture(name="framer")
def _framer_fixture() -> FramerRTU:
    """Return a *client‑side* RTU framer with the real decoder attached."""

    return FramerRTU(DecodePDU(is_server=False))


def _make_frame(framer: FramerRTU, device_id: int, pdu: bytes) -> bytes:
    """Helper – use the framer's *encode* to build a CRC‑correct frame."""

    return framer.encode(pdu, device_id, 0)


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
    """Skip garbage without discarding the complete frame that follows."""

    garbage = b"ABCD"
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


def test_ambiguous_garbage_waits(framer: FramerRTU):
    """An incomplete candidate cannot safely be distinguished from garbage."""
    good = _make_frame(framer, 0x10, bytes.fromhex("06 00 05 00 06"))
    # At offset 1 this looks like a Report Server ID response with 34 data
    # bytes. The following frame could be part of that response's payload.
    used, _, _, decoded = framer.decode(bytes.fromhex("ff ff 11 22") + good)
    assert used == 0
    assert decoded == framer.EMPTY


@pytest.mark.parametrize("prefix", [b"", b"ABCD"])
@pytest.mark.parametrize(
    ("is_server", "frame_hex", "function_code", "address", "registers"),
    [
        (False, "01 03 08 01 03 02 12 34 b5 33 00 d5 dc", 3, 0, [0x0103, 0x0212, 0x34B5, 0x3300]),
        (True, "01 10 00 00 00 04 08 01 06 12 34 56 78 f2 fe f6 71", 16, 0, [0x0106, 0x1234, 0x5678, 0xF2FE]),
    ],
)
def test_fragmented_frame_with_valid_frame_in_payload(prefix, is_server, frame_hex, function_code, address, registers):
    """Wait for the outer frame instead of treating its register data as a PDU."""
    framer = FramerRTU(DecodePDU(is_server))
    frame = bytes.fromhex(frame_hex)
    for length in range(1, len(frame)):
        used, pdu = framer.processIncomingFrame(prefix + frame[:length])
        assert used == 0
        assert pdu is None

    used, pdu = framer.processIncomingFrame(prefix + frame)
    assert used == len(prefix + frame)
    assert pdu.dev_id == 1
    assert pdu.function_code == function_code
    assert pdu.address == address
    assert pdu.registers == registers


@pytest.mark.parametrize("is_server", [False, True])
@pytest.mark.parametrize("message_hex", ["12 34", "12 34 56 78", "12 34 ef ec 56 78"])
def test_diagnostic_roundtrip(is_server, message_hex):
    """Preserve arbitrary diagnostic data, including a CRC-valid prefix."""
    framer = FramerRTU(DecodePDU(is_server))
    message_type = ReturnQueryDataRequest if is_server else ReturnQueryDataResponse
    message = bytes.fromhex(message_hex)
    frame = framer.buildFrame(message_type(message=message, dev_id=17))
    used, pdu = framer.processIncomingFrame(frame)
    assert used == len(frame)
    assert isinstance(pdu, message_type)
    assert pdu.dev_id == 17
    assert pdu.message == message


def test_modbus_plus_statistics_roundtrip(framer: FramerRTU):
    """The statistics response also reports a minimum RTU size."""
    prefix_crc = framer.compute_CRC(bytes.fromhex("11 08 00 15 00 03"))
    message = [3, prefix_crc] + [0] * 54
    frame = framer.buildFrame(GetClearModbusPlusResponse(message=message, dev_id=17))
    used, pdu = framer.processIncomingFrame(frame)
    assert used == len(frame)
    assert isinstance(pdu, GetClearModbusPlusResponse)
    assert pdu.message == tuple(message)


@pytest.mark.parametrize("suffix", [b"\x00", b"\x00\x00"])
@pytest.mark.parametrize("pdu_hex", ["06 00 01 00 03", "03 02 12 34", "08 00 0b 00 03"])
def test_exact_frame_followed_by_zero(framer: FramerRTU, pdu_hex, suffix):
    """Trailing zeros must not be included in frames with a known length."""
    encoded_pdu = bytes.fromhex(pdu_hex)
    frame = _make_frame(framer, 17, encoded_pdu)
    used, pdu = framer.processIncomingFrame(frame + suffix)
    assert used == len(frame)
    assert pdu.function_code == encoded_pdu[0]
    assert pdu.encode() == encoded_pdu[1:]
