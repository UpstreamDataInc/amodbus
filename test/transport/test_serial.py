"""Test the serialx integration and native serial transport."""

import asyncio
import os
import threading
from unittest import mock

import pytest
import serialx

from amodbus.client import ModbusSerialClient
from amodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from amodbus.server import ModbusSerialServer
from amodbus.transport import CommParams, CommType


@pytest.fixture(name="serial_params")
def serial_params_fixture():
    """Serial settings shared by client and listener tests."""
    return CommParams(
        comm_type=CommType.SERIAL,
        host="unknown://port",
        source_address=("unknown://port", 0),
        baudrate=19200,
        bytesize=7,
        parity="E",
        stopbits=2,
        timeout_connect=1,
    )


@pytest.mark.parametrize("is_server", [False, True])
async def test_serial_settings(dummy_protocol, serial_params, is_server):
    """Pass existing amodbus settings to serialx's native API."""
    protocol = dummy_protocol(serial_params, is_server)
    transport = mock.Mock(spec=serialx.BaseSerialTransport)
    with mock.patch("serialx.create_serial_connection", return_value=(transport, protocol)) as create:
        assert await (protocol.listen() if is_server else protocol.connect())
    create.assert_awaited_once_with(
        asyncio.get_running_loop(),
        protocol.handle_new_connection,
        "unknown://port",
        baudrate=19200,
        byte_size=7,
        parity=serialx.Parity.EVEN,
        stopbits=serialx.StopBits.TWO,
        exclusive=True,
    )
    protocol.close()
    transport.abort.assert_called_once()
    transport.close.assert_not_called()


@pytest.mark.parametrize("is_server", [False, True])
async def test_serial_backend_error(dummy_protocol, serial_params, is_server):
    """Serialx backend errors are connection failures, just like OS errors."""
    protocol = dummy_protocol(serial_params, is_server)
    assert not await (protocol.listen() if is_server else protocol.connect())
    assert not protocol.transport
    assert not protocol.active_connections
    protocol.close()


@pytest.mark.parametrize("cancel", [False, True])
async def test_serial_connect_cancel(dummy_protocol, serial_params, cancel):
    """Timeouts and cancellation reach the asynchronous serial opener."""
    protocol = dummy_protocol(serial_params)
    protocol.comm_params.timeout_connect = 0.05
    started = asyncio.Event()
    cleaned_up = asyncio.Event()

    async def delayed_connect(*_args, **_kwargs):
        started.set()
        try:
            await asyncio.Future()
        finally:
            cleaned_up.set()

    with mock.patch("serialx.create_serial_connection", side_effect=delayed_connect):
        task = asyncio.create_task(protocol.connect())
        await asyncio.wait_for(started.wait(), 1)
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            assert not await task
    assert cleaned_up.is_set()
    assert not protocol.transport
    protocol.close()


async def test_serial_reconnect_waits_for_close(dummy_protocol, serial_params):
    """A timeout waiting for close must not cancel the waiter's next use."""
    protocol = dummy_protocol(serial_params)
    protocol.comm_params.timeout_connect = 0.05
    closed = asyncio.get_running_loop().create_future()
    old_transport = mock.Mock(spec=serialx.BaseSerialTransport)

    async def wait_closed():
        await closed
        protocol.connection_lost(None)

    old_transport.wait_closed.side_effect = wait_closed
    protocol.connection_made(old_transport)
    protocol.close()
    new_transport = mock.Mock(spec=serialx.BaseSerialTransport)
    with mock.patch("serialx.create_serial_connection", return_value=(new_transport, protocol)) as create:
        assert not await protocol.connect()
        create.assert_not_awaited()
        assert not closed.cancelled()
        closed.set_result(None)
        assert await protocol.connect()
        assert protocol.transport is new_transport
        create.assert_awaited_once()
    protocol.close()


@pytest.fixture(name="serial_pty")
async def serial_pty_fixture():
    """Provide a real POSIX tty and an asynchronous reader for its peer."""
    if os.name != "posix":
        pytest.skip("Pseudo terminals require POSIX")
    master, slave = os.openpty()
    reader = asyncio.StreamReader()
    read_transport, _ = await asyncio.get_running_loop().connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(reader), os.fdopen(os.dup(master), "rb", buffering=0)
    )
    try:
        yield os.ttyname(slave), master, reader
    finally:
        read_transport.close()
        os.close(master)
        os.close(slave)


@pytest.fixture(name="serial_connection")
async def serial_connection_fixture(serial_pty, dummy_protocol):
    """Connect amodbus through the native platform serial transport."""
    path, _, _ = serial_pty
    protocol = dummy_protocol(
        CommParams(
            comm_type=CommType.SERIAL,
            host=path,
            baudrate=19200,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout_connect=2,
        )
    )
    received = asyncio.StreamReader()

    def receive(data, addr=None):
        received.feed_data(data)
        return len(data)

    protocol.callback_data = receive
    assert await protocol.connect()
    try:
        yield protocol, received
    finally:
        transport = protocol.transport or protocol._closing_serial_transport
        protocol.close()
        await asyncio.wait_for(transport.wait_closed(), 2)


@pytest.mark.parametrize("first_write", [0, 2, BlockingIOError()])
async def test_serial_partial_write(serial_connection, serial_pty, first_write):
    """A short or blocked OS write must preserve every outgoing byte."""
    protocol, received = serial_connection
    _, master, peer = serial_pty
    fd = protocol.transport.serial.fileno()
    write = os.write
    first = True

    def short_write(target, data):
        nonlocal first
        if target == fd:
            if first:
                first = False
                if isinstance(first_write, Exception):
                    raise first_write
                return write(target, data[:first_write])
            return write(target, data[:2])
        return write(target, data)

    data = b"serial data" * 10
    with mock.patch("os.write", side_effect=short_write):
        protocol.send(data)
        assert await asyncio.wait_for(peer.readexactly(len(data)), 2) == data
    os.write(master, b"response")
    assert await asyncio.wait_for(received.readexactly(8), 2) == b"response"


async def test_serial_close_discards_output(serial_connection, serial_pty):
    """Closing must discard a blocked request instead of draining it later."""
    protocol, _ = serial_connection
    _, _, peer = serial_pty
    transport = protocol.transport
    fd = transport.serial.fileno()
    write = os.write

    def blocked_write(target, data):
        if target == fd:
            raise BlockingIOError
        return write(target, data)

    with mock.patch("os.write", side_effect=blocked_write):
        protocol.send(b"unsent request")
        assert transport.get_write_buffer_size()
        protocol.close()
    await asyncio.wait_for(transport.wait_closed(), 2)
    assert not transport.get_write_buffer_size()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(peer.read(1), 0.05)


async def test_serial_immediate_reconnect(serial_connection, serial_pty):
    """Reopen an exclusive tty without a stale close callback losing it."""
    protocol, received = serial_connection
    _, master, peer = serial_pty
    old_transport = protocol.transport
    protocol.close()
    assert await protocol.connect()
    assert protocol.transport is not old_transport
    protocol.send(b"new request")
    assert await asyncio.wait_for(peer.readexactly(11), 2) == b"new request"
    os.write(master, b"new response")
    assert await asyncio.wait_for(received.readexactly(12), 2) == b"new response"


async def test_serial_cancel_open(serial_pty):
    """Cancel a slow device open, release its descriptor, and reopen it."""
    path, _, _ = serial_pty
    client = ModbusSerialClient(path, timeout=2)
    started = asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()
    open_port = os.open

    def delayed_open(target, *args, **kwargs):
        if target == path:
            loop.call_soon_threadsafe(started.set)
            assert release.wait(2)
        return open_port(target, *args, **kwargs)

    with mock.patch("os.open", side_effect=delayed_open):
        task = asyncio.create_task(client.connect())
        try:
            await asyncio.wait_for(started.wait(), 1)
            task.cancel()
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert not client.connected
    assert await client.connect()
    transport = client.ctx.transport
    client.close()
    await asyncio.wait_for(transport.wait_closed(), 2)


@pytest.mark.parametrize("local_echo", [False, True])
async def test_serial_rtu_response(serial_pty, local_echo):
    """Read a register through a tty with a fragmented response and echo."""
    path, master, peer = serial_pty
    client = ModbusSerialClient(path, timeout=2, retries=0, handle_local_echo=local_echo)
    assert await client.connect()
    transport = client.ctx.transport
    request_task = asyncio.create_task(client.read_holding_registers(0, count=1))
    try:
        request = await asyncio.wait_for(peer.readexactly(8), 2)
        assert request == bytes.fromhex("01 03 00 00 00 01 84 0a")
        if local_echo:
            os.write(master, request[:3])
            await asyncio.sleep(0.01)
            os.write(master, request[3:])
        os.write(master, bytes.fromhex("01 03 02"))
        await asyncio.sleep(0.01)
        os.write(master, bytes.fromhex("12 34 b5 33"))
        response = await asyncio.wait_for(request_task, 2)
        assert response.registers == [0x1234]
    finally:
        request_task.cancel()
        await asyncio.gather(request_task, return_exceptions=True)
        client.close()
        await asyncio.wait_for(transport.wait_closed(), 2)


async def test_serial_rtu_server(serial_pty):
    """Serve an RTU request through the native tty and reopen the listener."""
    path, master, peer = serial_pty
    store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0x1234] * 2))
    server = ModbusSerialServer(ModbusServerContext(slaves=store, single=True), port=path)
    try:
        for _ in range(2):
            assert await server.listen()
            os.write(master, bytes.fromhex("01 03 00 00 00 01 84 0a"))
            response = await asyncio.wait_for(peer.readexactly(7), 2)
            assert response == bytes.fromhex("01 03 02 12 34 b5 33")
            server.close()
    finally:
        transport = server.transport or server._closing_serial_transport
        await server.shutdown()
        if transport:
            await asyncio.wait_for(transport.wait_closed(), 2)
