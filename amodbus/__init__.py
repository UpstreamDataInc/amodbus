"""amodbus: Modbus Protocol Implementation.

Released under the BSD license
"""

__all__ = [
    "ExceptionResponse",
    "FramerType",
    "ModbusException",
    "__version__",
    "__version_full__",
    "amodbus_apply_logging_config",
]

from amodbus.exceptions import ModbusException
from amodbus.framer import FramerType
from amodbus.logging import amodbus_apply_logging_config
from amodbus.pdu import ExceptionResponse

__version__ = "3.9.0dev2"
__version_full__ = f"[amodbus, version {__version__}]"
