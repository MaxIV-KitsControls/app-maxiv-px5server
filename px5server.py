#!/usr/bin/env python3
"""Open a TCP server and forward requests to an Amptek PX5 device through USB.

This server must run as root in order to access the USB interface.
"""

# Imports

import os
import asyncio
import argparse
import contextlib
import functools

from usb.core import find
from usb.util import ENDPOINT_IN, ENDPOINT_OUT
from usb.util import endpoint_direction, find_descriptor, dispose_resources


# USB Constants

MAXSIZE = 2**16
VENDOR = 0x10c4
PRODUCT = 0x842a


# TCP constants

DEFAULT_BIND = ''
DEFAULT_PORT = 10001


# USB helpers

match_in = lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_IN
match_out = lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_OUT


@contextlib.contextmanager
def usb_endpoints(vendor, product):
    # Find device
    dev = find(idVendor=vendor, idProduct=product)
    if dev is None:
        raise IOError('Device not found')
    # Configuration
    dev.set_configuration()
    cfg = dev.get_active_configuration()
    intf = cfg[(0, 0)]
    # Endpoints
    epin = find_descriptor(intf, custom_match=match_in)
    epout = find_descriptor(intf, custom_match=match_out)
    if epin is None or epout is None:
        raise IOError('Endpoints not found')
    # Safe clean
    try:
        yield epin, epout
    finally:
        dispose_resources(dev)


def usb_request(request, epin, epout):
    # Write request
    epout.write(request)
    # Read reply
    return epin.read(MAXSIZE).tobytes()


# TCP client handler

@asyncio.coroutine
def handle_client(endpoints, reader, writer):
    loop = asyncio.get_event_loop()
    # Loop over requests
    try:
        while not reader.at_eof():
            # Wait next request
            try:
                header = yield from reader.readexactly(4)
            except EOFError:
                return
            # Read request
            msb, lsb = yield from reader.readexactly(2)
            data = yield from reader.readexactly(msb * 256 + lsb)
            checksum = yield from reader.readexactly(2)
            request = header + bytes((msb, lsb)) + data + checksum
            # Run request
            with (yield from loop.lock):
                reply = yield from loop.run_in_executor(
                    None, usb_request, request, *endpoints)
            # Write reply
            writer.write(reply)
    # Clean tcp interface
    finally:
        writer.close()


# TCP server

def run_server(bind=DEFAULT_BIND, port=DEFAULT_PORT,
               vendor=VENDOR, product=PRODUCT):
    # Check root user
    if os.geteuid() != 0:
        print('Server must run as root')
        return
    # Initialize loop
    loop = asyncio.get_event_loop()
    loop.lock = asyncio.Lock()
    # Initialize usb endpoints
    with usb_endpoints(vendor, product) as endpoints:
        handler = functools.partial(handle_client, endpoints)
        # Initialize server
        coro = asyncio.start_server(handler, bind, port)
        server = loop.run_until_complete(coro)
        msg = 'Serving on {0[0]} port {0[1]} ...'
        print(msg.format(server.sockets[0].getsockname()))
        # Run server
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        # Close server
        server.close()
        loop.run_until_complete(server.wait_closed())
        print('The server closed properly')


# Main execution

def main(args=None):
    parser = argparse.ArgumentParser(
        description=__doc__)
    parser.add_argument(
        '--bind', '-b', default=DEFAULT_BIND,
        help='Specify alternate bind address [default: all interfaces]')
    parser.add_argument(
        'port', action='store', default=DEFAULT_PORT, type=int, nargs='?',
        help='Specify alternate port [default: 10001]')
    args = parser.parse_args(args)
    return run_server(args.bind, args.port)

if __name__ == '__main__':
    main()
