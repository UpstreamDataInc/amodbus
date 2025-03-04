"""Modbus client async serial communication."""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Callable

from amodbus.client.base import ModbusBaseClient
from amodbus.framer import FramerType
from amodbus.pdu import ModbusPDU
from amodbus.transport import CommParams, CommType

with contextlib.suppress(ImportError):
    import serial


class ModbusSerialClient(ModbusBaseClient):
    """**ModbusSerialClient**.

    Fixed parameters:

    :param port: Serial port used for communication.

    Optional parameters:

    :param framer: Framer name, default FramerType.RTU
    :param baudrate: Bits per second.
    :param bytesize: Number of bits per byte 7-8.
    :param parity: 'E'ven, 'O'dd or 'N'one
    :param stopbits: Number of stop bits 1, 1.5, 2.
    :param handle_local_echo: Discard local echo from dongle.
    :param name: Set communication name, used in logging
    :param reconnect_delay: Minimum delay in seconds.milliseconds before reconnecting.
    :param reconnect_delay_max: Maximum delay in seconds.milliseconds before reconnecting.
    :param timeout: Timeout for connecting and receiving data, in seconds.
    :param retries: Max number of retries per request.
    :param trace_packet: Called with bytestream received/to be sent
    :param trace_pdu: Called with PDU received/to be sent
    :param trace_connect: Called when connected/disconnected

    .. tip::
        The trace methods allow to modify the datastream/pdu !

    .. tip::
        **reconnect_delay** doubles automatically with each unsuccessful connect, from
        **reconnect_delay** to **reconnect_delay_max**.
        Set `reconnect_delay=0` to avoid automatic reconnection.

    Example::

        from amodbus.client import ModbusSerialClient

        async def run():
            client = ModbusSerialClient("dev/serial0")

            await client.connect()
            ...
            client.close()

    Please refer to :ref:`amodbus internals` for advanced usage.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        port: str,
        *,
        framer: FramerType = FramerType.RTU,
        baudrate: int = 19200,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        handle_local_echo: bool = False,
        name: str = "comm",
        reconnect_delay: float = 0.1,
        reconnect_delay_max: float = 300,
        timeout: float = 3,
        retries: int = 3,
        trace_packet: Callable[[bool, bytes], bytes] | None = None,
        trace_pdu: Callable[[bool, ModbusPDU], ModbusPDU] | None = None,
        trace_connect: Callable[[bool], None] | None = None,
    ) -> None:
        """Initialize Asyncio Modbus Serial Client."""
        if "serial" not in sys.modules:  # pragma: no cover
            raise RuntimeError(
                "Serial client requires pyserial " 'Please install with "pip install pyserial" and try again.'
            )
        if framer not in [FramerType.ASCII, FramerType.RTU]:
            raise TypeError("Only FramerType RTU/ASCII allowed.")
        self.comm_params = CommParams(
            comm_type=CommType.SERIAL,
            host=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            handle_local_echo=handle_local_echo,
            comm_name=name,
            reconnect_delay=reconnect_delay,
            reconnect_delay_max=reconnect_delay_max,
            timeout_connect=timeout,
        )
        ModbusBaseClient.__init__(
            self,
            framer,
            retries,
            self.comm_params,
            trace_packet,
            trace_pdu,
            trace_connect,
        )
