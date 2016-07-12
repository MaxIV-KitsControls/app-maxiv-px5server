px5server
=========

A TCP server forwarding requests to an Amptek PX5 device through USB.


Requirements
------------

- Python >= 3.4
- [PyUSB](https://walac.github.io/pyusb/)


Usage
-----

```
$ python3 -m px5server --help
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

Performance
-----------

Tested with a Raspberry Pi and a 100M connection:

- Read a 1024-channel spectrum: 6ms (against 35 ms for UDP, according to the documentation)


Contact
-------

Ludwig Kjellsson: ludvig.kjellsson@maxiv.lu.se
Vincent Michel: vincent.michel@maxlab.lu.se
