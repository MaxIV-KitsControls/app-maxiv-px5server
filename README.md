px5server
=========

A TCP server forwarding requests to an Amptek PX5 device through USB.


Requirements
------------

The server is based on `asyncio` and `pyusb`:

- Python >= 3.4
- [PyUSB](https://walac.github.io/pyusb/)


Usage
-----

Run the `px5server` as a script or a python module:

```console
$ ./px5server.py --help  # Or python3 -m px5server --help
usage: px5server.py [-h] [--bind BIND] [port]

Open a TCP server and forward requests to an Amptek PX5 device through USB.
This server must run as root in order to access the USB interface.

positional arguments:
  port                  Specify alternate port [default: 10001]

optional arguments:
  -h, --help            show this help message and exit
  --bind BIND, -b BIND  Specify alternate bind address
                        [default: all interfaces]
```


Package
-------

A debian package can be built using the `package.sh` script.

This package provides:
- `/usr/bin/px5server` - the server as an executable
- `/etc/systemd/system/px5server.service` - the corresponding systemd service
- `/etc/udev/rules.d/10-usb.rules` - a set of udev rules to manage the service

The server then starts and stops automatically when the equipment is plugged
in and out. In order to install the package run:

```console
$ sudo dpkg -i px5server_X.Y.Z-N_all.deb
```


Debugging
---------

Check the logs by running

```console
$ sudo systemd px5server status # and
$ sudo journalctl -a -u px5server
```


Performance
-----------

Tested with a Raspberry Pi and a 100M connection:

- Read a 1024-channel spectrum: 6 ms (against 35 ms for UDP, according to the documentation)


Contact
-------

- Ludwig Kjellsson: ludvig.kjellsson@maxiv.lu.se
- Vincent Michel: vincent.michel@maxlab.lu.se
