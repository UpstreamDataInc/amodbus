"""Test events."""

import pytest

from amodbus.events import (
    CommunicationRestartEvent,
    EnteredListenModeEvent,
    RemoteReceiveEvent,
    RemoteSendEvent,
)
from amodbus.exceptions import ParameterException


class TestEvents:
    """Unittest for the amodbus.device module."""

    def test_remote_receive_event(self):
        """Test remove receive event."""
        event = RemoteReceiveEvent()
        event.decode(b"\x70")
        assert event.overrun
        assert event.listen
        assert event.broadcast

    def test_remote_sent_event(self):
        """Test remote sent event."""
        event = RemoteSendEvent()
        result = event.encode()
        assert result == b"\x40"
        event.decode(b"\x7f")
        assert event.read
        assert event.slave_abort
        assert event.slave_busy
        assert event.slave_nak
        assert event.write_timeout
        assert event.listen

    def test_remote_sent_event_encode(self):
        """Test remote sent event encode."""
        arguments = {
            "read": True,
            "slave_abort": True,
            "slave_busy": True,
            "slave_nak": True,
            "write_timeout": True,
            "listen": True,
        }
        event = RemoteSendEvent(**arguments)
        result = event.encode()
        assert result == b"\x7f"

    def test_entered_listen_mode_event(self):
        """Test entered listen mode event."""
        event = EnteredListenModeEvent()
        result = event.encode()
        assert result == b"\x04"
        event.decode(b"\x04")
        assert event.value == 0x04
        with pytest.raises(ParameterException):
            event.decode(b"\x00")

    def test_communication_restart_event(self):
        """Test communication restart event."""
        event = CommunicationRestartEvent()
        result = event.encode()
        assert result == b"\x00"
        event.decode(b"\x00")
        assert not event.value
        with pytest.raises(ParameterException):
            event.decode(b"\x04")
