"""Test transaction."""

import asyncio
from unittest import mock

import pytest

from amodbus.exceptions import ConnectionException, ModbusIOException
from amodbus.framer import FramerRTU, FramerSocket
from amodbus.pdu import DecodePDU, ExceptionResponse
from amodbus.pdu.bit_message import ReadCoilsRequest, ReadCoilsResponse
from amodbus.transaction import TransactionManager


@pytest.mark.parametrize("use_port", [5098])
class TestTransaction:
    """Test the amodbus.transaction module."""

    async def test_transaction_instance(self, use_clc):
        """Test instantiate class."""
        TransactionManager(
            use_clc,
            FramerRTU(DecodePDU(False)),
            5,
            False,
            None,
            None,
            None,
        )
        TransactionManager(
            use_clc,
            FramerRTU(DecodePDU(True)),
            5,
            True,
            None,
            None,
            None,
        )

    async def test_transaction_manager_tid(self, use_clc):
        """Test next TID."""
        transact = TransactionManager(
            use_clc,
            FramerRTU(DecodePDU(False)),
            5,
            False,
            None,
            None,
            None,
        )
        assert transact.getNextTID() == 1
        for tid in range(2, 12):
            assert tid == transact.getNextTID()
        assert transact.getNextTID() == 12
        transact.next_tid = 64999
        assert transact.getNextTID() == 65000
        assert transact.getNextTID() == 1

    async def test_transaction_calls(self, use_clc):
        """Test dummy calls from transport."""
        transact = TransactionManager(
            use_clc,
            FramerRTU(DecodePDU(False)),
            5,
            False,
            None,
            None,
            None,
        )
        transact.callback_new_connection()
        transact.callback_connected()

    async def test_transaction_disconnect(self, use_clc):
        """Test tracers in disconnect."""
        transact = TransactionManager(
            use_clc,
            FramerRTU(DecodePDU(False)),
            5,
            False,
            None,
            None,
            None,
        )
        transact.trace_packet = mock.Mock()
        transact.trace_pdu = mock.Mock()
        transact.trace_connect = mock.Mock()
        transact.callback_disconnected(None)
        transact.trace_connect.assert_called_once_with(False)
        transact.trace_packet.assert_not_called()
        transact.trace_pdu.assert_not_called()

    @pytest.mark.parametrize(("test", "is_server"), [(True, False), (False, False), (True, True)])
    async def test_transaction_data(self, use_clc, test, is_server):
        """Test tracers in disconnect."""
        pdu = ExceptionResponse(0xFF)
        pdu.dev_id = 0
        packet = b"\x00\x03\x00\x7c\x00\x02\x04\x02"
        transact = TransactionManager(
            use_clc,
            FramerRTU(DecodePDU(False)),
            5,
            False,
            None,
            None,
            None,
        )
        transact.is_server = is_server
        transact.framer.processIncomingFrame = mock.Mock(return_value=(0, None))
        transact.callback_data(packet)
        assert not transact.response_future.done()

        if test:
            transact.trace_packet = mock.Mock(return_value=packet)
            transact.framer.processIncomingFrame.return_value = (1, pdu)
            transact.callback_data(packet)
            transact.trace_packet.assert_called_once_with(False, packet)
        else:
            transact.trace_packet = mock.Mock(return_value=packet)
            transact.trace_pdu = mock.Mock(return_value=pdu)
            transact.framer.processIncomingFrame.return_value = (1, pdu)
            transact.callback_data(packet)
            transact.trace_packet.assert_called_with(False, packet)
            transact.trace_pdu.assert_called_once_with(False, pdu)
            assert transact.response_future.result() == pdu

    @pytest.mark.parametrize("test", [True, False])
    async def test_transaction_data_2(self, use_clc, test):
        """Test tracers in disconnect."""
        pdu = ExceptionResponse(0xFF)
        packet = b"\x00\x03\x00\x7c\x00\x02\x04\x02"
        transact = TransactionManager(
            use_clc,
            FramerRTU(DecodePDU(False)),
            5,
            False,
            None,
            None,
            None,
        )
        transact.framer.processIncomingFrame = mock.Mock()
        transact.trace_packet = mock.Mock(return_value=packet)
        transact.framer.processIncomingFrame.return_value = (1, pdu)
        if test:
            pdu.dev_id = 17
        else:
            pdu.dev_id = 0
            transact.response_future.set_result((1, pdu))
        with pytest.raises(ModbusIOException):
            transact.callback_data(packet)

    @pytest.mark.parametrize("scenario", range(8))
    async def test_transaction_execute(self, use_clc, scenario):
        """Test tracers in disconnect."""
        transact = TransactionManager(
            use_clc,
            FramerRTU(DecodePDU(False)),
            5,
            False,
            None,
            None,
            None,
        )
        transact.send = mock.Mock()
        request = ReadCoilsRequest(address=117, count=5, dev_id=1)
        response = ReadCoilsResponse(bits=[True, False, True, True, False], dev_id=1)
        transact.retries = 0
        transact.connection_made(mock.AsyncMock())
        transact.transport.write = mock.Mock()
        if scenario == 0:  # transport not ok and no connect
            transact.transport = None
            with pytest.raises(ConnectionException):
                await transact.execute(False, request)
        elif scenario == 1:  # transport not ok and connect, no trace
            transact.transport = None
            transact.connect = mock.AsyncMock(return_value=1)
            await transact.execute(True, request)
        elif scenario == 2:  # transport ok, trace and send
            transact.trace_pdu = mock.Mock(return_value=request)
            transact.trace_packet = mock.Mock(return_value=b"123")
            await transact.execute(True, request)
            transact.trace_pdu.assert_called_once_with(True, request)
            transact.trace_packet.assert_called_once_with(True, b"\x01\x01\x00u\x00\x05\xed\xd3")
        elif scenario == 3:  # wait receive,timeout, no_responses
            transact.comm_params.timeout_connect = 0.1
            transact.count_no_responses = 10
            transact.connection_lost = mock.Mock()
            with pytest.raises(ModbusIOException):
                await transact.execute(False, request)
        elif scenario == 4:  # wait receive,timeout, disconnect
            transact.comm_params.timeout_connect = 0.1
            transact.count_no_responses = 10
            transact.count_until_disconnect = -1
            transact.connection_lost = mock.Mock()
            with pytest.raises(ModbusIOException):
                await transact.execute(False, request)
        elif scenario == 5:  # wait receive,timeout, no_responses pass
            transact.comm_params.timeout_connect = 0.1
            transact.connection_lost = mock.Mock()
            with pytest.raises(ModbusIOException):
                await transact.execute(False, request)
        elif scenario == 6:  # wait receive, cancel
            transact.comm_params.timeout_connect = 0.2
            resp = asyncio.create_task(transact.execute(False, request))
            await asyncio.sleep(0.1)
            resp.cancel()
            await asyncio.sleep(0.1)
            with pytest.raises(asyncio.CancelledError):
                await resp
        else:  # if scenario == 7: # response
            transact.comm_params.timeout_connect = 0.2
            resp = asyncio.create_task(transact.execute(False, request))
            await asyncio.sleep(0.1)
            transact.response_future.set_result(response)
            await asyncio.sleep(0.1)
            assert response == await resp

    async def test_transaction_receiver(self, use_clc):
        """Test tracers in disconnect."""
        transact = TransactionManager(
            use_clc,
            FramerSocket(DecodePDU(False)),
            5,
            False,
            None,
            None,
            None,
        )
        transact.send = mock.Mock()
        response = ReadCoilsResponse(bits=[True, False, True, True, False], dev_id=0)
        transact.retries = 0
        transact.connection_made(mock.AsyncMock())

        data = b"\x00\x00\x12\x34\x00\x06\x00\x01\x01\x02\x00\x04"
        transact.data_received(data)
        response = await transact.response_future
        assert isinstance(response, ReadCoilsResponse)

    @pytest.mark.parametrize("no_resp", [False, True])
    async def test_client_protocol_execute_outside(self, use_clc, no_resp):
        """Test the transaction execute method."""
        transact = TransactionManager(
            use_clc,
            FramerSocket(DecodePDU(False)),
            5,
            False,
            None,
            None,
            None,
        )
        transact.send = mock.Mock()
        request = ReadCoilsRequest(address=117, count=5, dev_id=1)
        transact.retries = 0
        transact.connection_made(mock.AsyncMock())
        transact.transport.write = mock.Mock()
        resp = asyncio.create_task(transact.execute(no_resp, request))
        await asyncio.sleep(0.2)
        data = b"\x00\x00\x12\x34\x00\x06\x01\x01\x01\x02\x00\x04"
        transact.data_received(data)
        result = await resp
        if no_resp:
            assert result.isError()
            assert isinstance(result, ExceptionResponse)
        else:
            assert not result.isError()
            assert isinstance(result, ReadCoilsResponse)

    async def test_transaction_id0(self, use_clc):
        """Test tracers in disconnect."""
        transact = TransactionManager(
            use_clc,
            FramerRTU(DecodePDU(False)),
            5,
            False,
            None,
            None,
            None,
        )
        transact.send = mock.Mock()
        request = ReadCoilsRequest(address=117, count=5, dev_id=1)
        response = ReadCoilsResponse(bits=[True, False, True, True, False], dev_id=0)
        transact.retries = 0
        transact.connection_made(mock.AsyncMock())
        transact.transport.write = mock.Mock()
        transact.comm_params.timeout_connect = 0.2
        resp = asyncio.create_task(transact.execute(False, request))
        await asyncio.sleep(0.1)
        transact.response_future.set_result(response)
        await asyncio.sleep(0.1)
        with pytest.raises(ModbusIOException):
            await resp
        response = ReadCoilsResponse(bits=[True, False, True, True, False], dev_id=1)
        transact.retries = 0
        transact.connection_made(mock.AsyncMock())
        transact.transport.write = mock.Mock()
        transact.comm_params.timeout_connect = 0.2
        resp = asyncio.create_task(transact.execute(False, request))
        await asyncio.sleep(0.1)
        transact.response_future.set_result(response)
        await asyncio.sleep(0.1)
        assert response == await resp
