"""Test other messages."""

from unittest import mock

import amodbus.pdu.other_message as amodbus_message


class TestOtherMessage:
    """Unittest for the amodbus.other_message module."""

    requests = [
        amodbus_message.ReadExceptionStatusRequest,
        amodbus_message.GetCommEventCounterRequest,
        amodbus_message.GetCommEventLogRequest,
        amodbus_message.ReportSlaveIdRequest,
    ]

    responses = [
        amodbus_message.ReadExceptionStatusResponse(0x12),
        amodbus_message.GetCommEventCounterResponse(0x12),
        amodbus_message.GetCommEventLogResponse,
        amodbus_message.ReportSlaveIdResponse(0x12),
    ]

    def test_other_messages_to_string(self):
        """Test other messages to string."""
        for message in self.requests:
            assert str(message)
        for message in self.responses:
            assert str(message)

    async def test_read_exception_status(self):
        """Test read exception status."""
        request = amodbus_message.ReadExceptionStatusRequest()
        request.decode(b"\x12")
        assert not request.encode()
        assert (await request.update_datastore(None)).function_code == 0x07

        response = amodbus_message.ReadExceptionStatusResponse(status=0x12)
        assert response.encode() == b"\x12"
        response.decode(b"\x12")
        assert response.status == 0x12

    async def test_get_comm_event_counter(self):
        """Test get comm event counter."""
        request = amodbus_message.GetCommEventCounterRequest()
        request.decode(b"\x12")
        assert not request.encode()
        assert (await request.update_datastore(None)).function_code == 0x0B

        response = amodbus_message.GetCommEventCounterResponse(count=0x12)
        assert response.encode() == b"\x00\x00\x00\x12"
        response.decode(b"\x00\x00\x00\x12")
        assert response.status
        assert response.count == 0x12

        response.status = False
        assert response.encode() == b"\xFF\xFF\x00\x12"

    async def test_get_comm_event_log(self):
        """Test get comm event log."""
        request = amodbus_message.GetCommEventLogRequest()
        request.decode(b"\x12")
        assert not request.encode()
        assert (await request.update_datastore(None)).function_code == 0x0C

        response = amodbus_message.GetCommEventLogResponse()
        assert response.encode() == b"\x06\x00\x00\x00\x00\x00\x00"
        response.decode(b"\x06\x00\x00\x00\x12\x00\x12")
        assert response.status
        assert response.message_count == 0x12
        assert response.event_count == 0x12
        assert not response.events

        response.status = False
        assert response.encode() == b"\x06\xff\xff\x00\x12\x00\x12"

    def test_get_comm_event_log_with_events(self):
        """Test get comm event log with events."""
        response = amodbus_message.GetCommEventLogResponse(events=[0x12, 0x34, 0x56])
        assert response.encode() == b"\x09\x00\x00\x00\x00\x00\x00\x12\x34\x56"
        response.decode(b"\x09\x00\x00\x00\x12\x00\x12\x12\x34\x56")
        assert response.status
        assert response.message_count == 0x12
        assert response.event_count == 0x12
        assert response.events == [0x12, 0x34, 0x56]

    async def test_report_slave_id_request(self):
        """Test report slave id request."""
        with mock.patch("amodbus.pdu.other_message.DeviceInformationFactory") as dif:
            # First test regular identity strings
            identity = {
                0x00: "VN",  # VendorName
                0x01: "PC",  # ProductCode
                0x02: "REV",  # MajorMinorRevision
                0x03: "VU",  # VendorUrl
                0x04: "PN",  # ProductName
                0x05: "MN",  # ModelName
                0x06: "UAN",  # UserApplicationName
                0x07: "RA",  # reserved
                0x08: "RB",  # reserved
            }
            dif.get.return_value = identity
            expected_identity = "-".join(identity.values()).encode()

            request = amodbus_message.ReportSlaveIdRequest()
            response = await request.update_datastore(None)
            assert response.identifier == expected_identity

            # Change to byte strings and test again (final result should be the same)
            identity = {
                0x00: b"VN",  # VendorName
                0x01: b"PC",  # ProductCode
                0x02: b"REV",  # MajorMinorRevision
                0x03: b"VU",  # VendorUrl
                0x04: b"PN",  # ProductName
                0x05: b"MN",  # ModelName
                0x06: b"UAN",  # UserApplicationName
                0x07: b"RA",  # reserved
                0x08: b"RB",  # reserved
            }
            dif.get.return_value = identity

            request = amodbus_message.ReportSlaveIdRequest()
            response = await request.update_datastore(None)
            assert response.identifier == expected_identity

    async def test_report_slave_id(self):
        """Test report slave id."""
        with mock.patch("amodbus.pdu.other_message.DeviceInformationFactory") as dif:
            dif.get.return_value = {}
            request = amodbus_message.ReportSlaveIdRequest()
            request.decode(b"\x12")
            assert not request.encode()
            assert (await request.update_datastore(None)).function_code == 0x11

            response = amodbus_message.ReportSlaveIdResponse((await request.update_datastore(None)).identifier, True)

            assert response.encode() == b"\x08amodbus\xff"
            response.decode(b"\x03\x12\x00")
            assert not response.status
            assert response.identifier == b"\x12\x00"

            response.status = False
            assert response.encode() == b"\x03\x12\x00\x00"
