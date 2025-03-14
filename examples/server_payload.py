#!/usr/bin/env python3
"""amodbus Server Payload Example.

This example shows how to initialize a server with a
complicated memory layout using builder.
"""
import asyncio
import logging
import sys

try:
    import server_async  # type: ignore[import-not-found]
except ImportError:
    print(
        "*** ERROR --> THIS EXAMPLE needs the example directory, please see \n\
          https://amodbus.readthedocs.io/en/latest/source/examples.html\n\
          for more information."
    )
    sys.exit(-1)


from amodbus.constants import Endian
from amodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from amodbus.payload import BinaryPayloadBuilder

_logger = logging.getLogger(__name__)


def setup_payload_server(cmdline=None):
    """Define payload for server and do setup."""
    # ----------------------------------------------------------------------- #
    # build your payload
    # ----------------------------------------------------------------------- #
    builder = BinaryPayloadBuilder(byteorder=Endian.LITTLE, wordorder=Endian.LITTLE)
    builder.add_string("abcdefgh")
    builder.add_bits([False, True, False, True, True, False, True, False])
    builder.add_8bit_int(-0x12)
    builder.add_8bit_uint(0x12)
    builder.add_16bit_int(-0x5678)
    builder.add_16bit_uint(0x1234)
    builder.add_32bit_int(-0x1234)
    builder.add_32bit_uint(0x12345678)
    builder.add_16bit_float(12.34)
    builder.add_16bit_float(-12.34)
    builder.add_32bit_float(22.34)
    builder.add_32bit_float(-22.34)
    builder.add_64bit_int(-0xDEADBEEF)
    builder.add_64bit_uint(0x12345678DEADBEEF)
    builder.add_64bit_uint(0xDEADBEEFDEADBEED)
    builder.add_64bit_float(123.45)
    builder.add_64bit_float(-123.45)

    # ----------------------------------------------------------------------- #
    # use that payload in the data store
    # Here we use the same reference block for each underlying store.
    # ----------------------------------------------------------------------- #

    block = ModbusSequentialDataBlock(1, builder.to_registers())
    store = ModbusSlaveContext(di=block, co=block, hr=block, ir=block)
    context = ModbusServerContext(slaves=store, single=True)
    return server_async.setup_server(description="Run payload server.", cmdline=cmdline, context=context)


async def main(cmdline=None):
    """Combine setup and run."""
    run_args = setup_payload_server(cmdline=cmdline)
    await server_async.run_async_server(run_args)


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
