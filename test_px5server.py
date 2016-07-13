import io
import runpy
import array
import pytest
import asyncio
import unittest
import px5server

NB_CLIENTS = 100


def test_request(mocker, event_loop, unused_tcp_port):
    # Mock usb library
    mocker.patch('os.geteuid').return_value = 0
    mocker.patch('px5server.find')
    mocker.patch('px5server.dispose_resources')
    find_descriptor = mocker.patch('px5server.find_descriptor')
    endpoint = find_descriptor.return_value

    # Client coroutine

    @asyncio.coroutine
    def client(n):
        # Wait for the server to start
        yield from asyncio.sleep(0.1)
        # Open connection
        reader, writer = yield from asyncio.open_connection(
            'localhost', unused_tcp_port)
        # Define request and reply
        request = bytes(range(4)) + bytes([0, n]) + bytes(range(n+2))
        reply = bytes(range(4)) + bytes([0, n]) + bytes(range(n+2))[::-1]
        # Write request
        request = bytes(range(4)) + bytes([0, n]) + bytes(range(n+2))
        writer.write(request[:n])
        writer.write(request[n:])
        # Read reply
        data = yield from reader.readexactly(len(reply))
        assert data == reply
        # Check request
        assert unittest.mock.call(request) in endpoint.write.call_args_list
        # Close connection
        writer.close()

    # Echo request function

    def echo_request(size):
        request = endpoint.write.call_args[0][0]
        return array.array('B', request[:6] + request[:5:-1])

    # Sigint function

    def sigint():
        raise KeyboardInterrupt

    # Configure asyncio and mock
    asyncio.set_event_loop(event_loop)
    endpoint.read = echo_request
    # Prepare N client
    coros = [client(n) for n in range(NB_CLIENTS)]
    task = asyncio.async(asyncio.gather(*coros))
    # Send KeyboardInterrupt when finished
    task.add_done_callback(lambda fut: sigint())
    # Run server
    px5server.run_server(port=unused_tcp_port)
    # Raise asserts
    assert task.done()
    task.result()


def test_root_user():
    with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as stdout:
        px5server.run_server()
    assert stdout.getvalue() == 'Server must run as root\n'


def test_main_function(mocker):
    run = mocker.patch('px5server.run_server')
    mocker.patch('sys.argv', ['px5server.py'])
    px5server.main()
    run.assert_called_once_with(px5server.DEFAULT_BIND, px5server.DEFAULT_PORT)


def test_main_module(mocker):
    mocker.patch('sys.argv', ['px5server.py', '--help'])
    with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as stdout:
        with pytest.raises(SystemExit):
            runpy.run_module('px5server', run_name='__main__')
    description = px5server.__doc__.splitlines()[0]
    assert description in stdout.getvalue()


def test_usb_endpoints(mocker):
    # Mock pyusb
    vendor, product = 0x1, 0x2
    find = mocker.patch('px5server.find')
    device = find.return_value
    find_descriptor = mocker.patch('px5server.find_descriptor')
    descriptor = find_descriptor.return_value
    # Device not found
    find.return_value = None
    with pytest.raises(IOError) as context:
        px5server.create_endpoints(vendor, product)
    assert 'Device not found' in str(context.value)
    find.return_value = device
    # Descriptor not found
    find_descriptor.return_value = None
    with pytest.raises(IOError) as context:
        px5server.create_endpoints(vendor, product)
    assert 'Endpoints not found' in str(context.value)
    find_descriptor.return_value = descriptor
    # Descriptor found
    a, b = px5server.create_endpoints(vendor, product)
    assert a == b == descriptor
    find.assert_called_with(idVendor=vendor, idProduct=product)
