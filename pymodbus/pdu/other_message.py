"""Diagnostic record read/write.

Currently not all implemented
"""

import struct

from pymodbus.constants import ModbusStatus
from pymodbus.datastore import ModbusSlaveContext
from pymodbus.device import DeviceInformationFactory, ModbusControlBlock
from pymodbus.pdu.pdu import ModbusPDU


_MCB = ModbusControlBlock()


class ReadExceptionStatusRequest(ModbusPDU):
    """ReadExceptionStatusRequest."""

    function_code = 0x07
    rtu_frame_size = 4

    def encode(self) -> bytes:
        """Encode the message."""
        return b""

    def decode(self, data: bytes) -> None:
        """Decode data part of the message."""

    async def update_datastore(self, _context: ModbusSlaveContext) -> ModbusPDU:
        """Run a read exception status request against the store."""
        status = _MCB.Counter.summary()
        return ReadExceptionStatusResponse(status=status, slave_id=self.slave_id, transaction_id=self.transaction_id)


class ReadExceptionStatusResponse(ModbusPDU):
    """ReadExceptionStatusResponse."""

    function_code = 0x07
    rtu_frame_size = 5

    def encode(self) -> bytes:
        """Encode the response."""
        return struct.pack(">B", self.status)

    def decode(self, data: bytes) -> None:
        """Decode a the response."""
        self.status = int(data[0])


# Encapsulate interface transport 43, 14
# CANopen general reference 43, 13

class GetCommEventCounterRequest(ModbusPDU):
    """GetCommEventCounterRequest."""

    function_code = 0x0B
    rtu_frame_size = 4

    def encode(self) -> bytes:
        """Encode the message."""
        return b""

    def decode(self, _data: bytes) -> None:
        """Decode data part of the message."""

    async def update_datastore(self, _context) -> ModbusPDU:
        """Run a read exception status request against the store."""
        count = _MCB.Counter.Event
        return GetCommEventCounterResponse(count=count, slave_id=self.slave_id, transaction_id=self.transaction_id)


class GetCommEventCounterResponse(ModbusPDU):
    """GetCommEventCounterRequest."""

    function_code = 0x0B
    rtu_frame_size = 8

    def encode(self) -> bytes:
        """Encode the response."""
        ready = ModbusStatus.READY if self.status else ModbusStatus.WAITING
        return struct.pack(">HH", ready, self.count)

    def decode(self, data: bytes) -> None:
        """Decode a the response."""
        ready, self.count = struct.unpack(">HH", data)
        self.status = ready == ModbusStatus.READY


class GetCommEventLogRequest(ModbusPDU):
    """GetCommEventLogRequest."""

    function_code = 0x0C
    rtu_frame_size = 4

    def encode(self) -> bytes:
        """Encode the message."""
        return b""

    def decode(self, _data: bytes) -> None:
        """Decode data part of the message."""

    async def update_datastore(self, _context: ModbusSlaveContext) -> ModbusPDU:
        """Run a read exception status request against the store."""
        return GetCommEventLogResponse(
            status=True,
            message_count=_MCB.Counter.BusMessage,
            event_count=_MCB.Counter.Event,
            events=_MCB.getEvents(),
            slave_id=self.slave_id, transaction_id=self.transaction_id)


class GetCommEventLogResponse(ModbusPDU):
    """GetCommEventLogRequest."""

    function_code = 0x0C
    rtu_byte_count_pos = 2

    def __init__(self, status=True, message_count=0, event_count=0, events=None, slave_id=1, transaction_id=0) -> None:
        """Initialize a new instance."""
        super().__init__(transaction_id=transaction_id, slave_id=slave_id, status=status)
        self.message_count = message_count
        self.event_count = event_count
        self.events = events if events else []

    def encode(self) -> bytes:
        """Encode the response."""
        if self.status:
            ready = ModbusStatus.READY
        else:
            ready = ModbusStatus.WAITING
        packet = struct.pack(">B", 6 + len(self.events))
        packet += struct.pack(">H", ready)
        packet += struct.pack(">HH", self.event_count, self.message_count)
        packet += b"".join(struct.pack(">B", e) for e in self.events)
        return packet

    def decode(self, data: bytes) -> None:
        """Decode a the response."""
        length = int(data[0])
        status = struct.unpack(">H", data[1:3])[0]
        self.status = status == ModbusStatus.READY
        self.event_count = struct.unpack(">H", data[3:5])[0]
        self.message_count = struct.unpack(">H", data[5:7])[0]

        self.events = []
        for i in range(7, length + 1):
            self.events.append(int(data[i]))


class ReportSlaveIdRequest(ModbusPDU):
    """ReportSlaveIdRequest."""

    function_code = 0x11
    rtu_frame_size = 4

    def encode(self) -> bytes:
        """Encode the message."""
        return b""

    def decode(self, _data: bytes) -> None:
        """Decode data part of the message."""

    async def update_datastore(self, context: ModbusSlaveContext) -> ModbusPDU:
        """Run a report slave id request against the store."""
        report_slave_id_data = None
        if context:
            report_slave_id_data = getattr(context, "reportSlaveIdData", None)
        if not report_slave_id_data:
            information = DeviceInformationFactory.get(_MCB)

            # Support identity values as bytes data and regular str data
            id_data = []
            for v_item in information.values():
                if isinstance(v_item, bytes):
                    id_data.append(v_item)
                else:
                    id_data.append(v_item.encode())

            identifier = b"-".join(id_data)
            identifier = identifier or b"Pymodbus"
            report_slave_id_data = identifier
        return ReportSlaveIdResponse(identifier=report_slave_id_data, slave_id=self.slave_id, transaction_id=self.transaction_id)


class ReportSlaveIdResponse(ModbusPDU):
    """ReportSlaveIdRequeste."""

    function_code = 0x11
    rtu_byte_count_pos = 2

    def __init__(self, identifier=b"\x00", status=True, slave_id=1, transaction_id=0) -> None:
        """Initialize a new instance."""
        super().__init__(transaction_id=transaction_id, slave_id=slave_id, status=status)
        self.identifier = identifier
        self.byte_count = 0

    def encode(self) -> bytes:
        """Encode the response."""
        status = ModbusStatus.SLAVE_ON if self.status else ModbusStatus.SLAVE_OFF
        length = len(self.identifier) + 1
        packet = struct.pack(">B", length)
        packet += self.identifier  # we assume it is already encoded
        packet += struct.pack(">B", status)
        return packet

    def decode(self, data: bytes) -> None:
        """Decode a the response.

        Since the identifier is device dependent, we just return the
        raw value that a user can decode to whatever it should be.
        """
        self.byte_count = int(data[0])
        self.identifier = data[1 : self.byte_count + 1]
        status = int(data[-1])
        self.status = status == ModbusStatus.SLAVE_ON
