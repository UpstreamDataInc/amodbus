"""Test exceptions."""
import pytest

from amodbus.exceptions import (
    ConnectionException,
    ModbusException,
    ModbusIOException,
    NotImplementedException,
    ParameterException,
)


class TestExceptions:  # pylint: disable=too-few-public-methods
    """Unittest for the amodbus.exceptions module."""

    exceptions = [
        ModbusException("bad base"),
        ModbusIOException("bad register"),
        ParameterException("bad parameter"),
        NotImplementedException("bad function"),
        ConnectionException("bad connection"),
    ]

    def test_exceptions(self):
        """Test all module exceptions."""
        for exc in self.exceptions:
            with pytest.raises(ModbusException, match="Modbus Error:"):
                raise exc
