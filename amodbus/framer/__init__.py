"""Framer."""

__all__ = [
    "FramerAscii",
    "FramerBase",
    "FramerRTU",
    "FramerSocket",
    "FramerTLS",
    "FramerType",
]

from amodbus.framer.ascii import FramerAscii
from amodbus.framer.base import FramerBase, FramerType
from amodbus.framer.rtu import FramerRTU
from amodbus.framer.socket import FramerSocket
from amodbus.framer.tls import FramerTLS

FRAMER_NAME_TO_CLASS = {
    FramerType.ASCII: FramerAscii,
    FramerType.RTU: FramerRTU,
    FramerType.SOCKET: FramerSocket,
    FramerType.TLS: FramerTLS,
}
