#!/usr/bin/env python3
"""Open a TCP server and forward requests to an Amptek PX5 device through USB.

This server must run as root in order to access the USB interface.
"""

# Imports

import os
import asyncio
import argparse
import collections

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


# Cache helpers

Cache = collections.namedtuple('Cache', 'get close clear')


def make_cache(get, close):
    cache = {}
    counter = collections.defaultdict(int)

    def cached_get(*args):
        if args not in cache:
            cache[args] = get(*args)
        counter[args] += 1
        return cache[args]

    def cached_close(*args):
        counter[args] -= 1
        if counter[args] == 0:
            del cache[args]
            close(*args)

    def clear():
        cache.clear()
        counter.clear()

    return Cache(cached_get, cached_close, clear)


# USB helpers

match_in = lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_IN
match_out = lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_OUT


def create_endpoints(vendor, product):
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
    return epin, epout


def close_device(vendor, product):
    # Find device
    dev = find(idVendor=vendor, idProduct=product)
    # Dispose resources
    dispose_resources(dev)


def usb_request(request, epin, epout):
    # Write request
    epout.write(request)
    # Read reply
    return epin.read(MAXSIZE).tobytes()


# TCP client handler

@asyncio.coroutine
def handle_client(reader, writer):
    loop = asyncio.get_event_loop()
    # Make usb interface
    try:
        endpoints = loop.get_endpoints()
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
                data = yield from reader.readexactly(msb * 16 + lsb)
                checksum = yield from reader.readexactly(2)
                request = header + bytes((msb, lsb)) + data + checksum
                # Run request
                with (yield from loop.lock):
                    reply = yield from loop.run_in_executor(
                        None, usb_request, request, *endpoints)
                # Write reply
                writer.write(reply)
        # Clean usb interface
        finally:
            loop.close_endpoints()
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
    cache = make_cache(create_endpoints, close_device)
    loop.get_endpoints = lambda: cache.get(vendor, product)
    loop.close_endpoints = lambda: cache.close(vendor, product)
    loop.lock = asyncio.Lock()
    # Initialize server
    coro = asyncio.start_server(handle_client, bind, port)
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
    cache.clear()
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
