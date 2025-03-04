"""Modbus client async TCP communication."""

from __future__ import annotations

from collections.abc import Callable

from amodbus.client.base import ModbusBaseClient
from amodbus.framer import FramerType
from amodbus.pdu import ModbusPDU
from amodbus.transport import CommParams, CommType


class ModbusTcpClient(ModbusBaseClient):
    """**ModbusTcpClient**.

    Fixed parameters:

    :param host: Host IP address or host name

    Optional parameters:

    :param framer: Framer name, default FramerType.SOCKET
    :param port: Port used for communication
    :param name: Set communication name, used in logging
    :param source_address: source address of client
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

        from amodbus.client import ModbusTcpClient

        async def run():
            client = ModbusTcpClient("localhost")

            await client.connect()
            ...
            client.close()

    Please refer to :ref:`amodbus internals` for advanced usage.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        host: str,
        *,
        framer: FramerType = FramerType.SOCKET,
        port: int = 502,
        name: str = "comm",
        source_address: tuple[str, int] | None = None,
        reconnect_delay: float = 0.1,
        reconnect_delay_max: float = 300,
        timeout: float = 3,
        retries: int = 3,
        trace_packet: Callable[[bool, bytes], bytes] | None = None,
        trace_pdu: Callable[[bool, ModbusPDU], ModbusPDU] | None = None,
        trace_connect: Callable[[bool], None] | None = None,
    ) -> None:
        """Initialize Asyncio Modbus TCP Client."""
        if not hasattr(self, "comm_params"):
            if framer not in [FramerType.SOCKET, FramerType.RTU, FramerType.ASCII]:
                raise TypeError("Only FramerType SOCKET/RTU/ASCII allowed.")
            self.comm_params = CommParams(
                comm_type=CommType.TCP,
                host=host,
                port=port,
                comm_name=name,
                source_address=source_address,
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
