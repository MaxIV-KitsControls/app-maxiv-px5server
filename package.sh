#!/bin/bash
# Dirty script to create rpi deb for px5server
cd `dirname $0`

# Executable
mkdir -p tmp/usr/bin
cp px5server.py tmp/usr/bin/px5server
chmod +x tmp/usr/bin/px5server

# Service
mkdir -p tmp/etc/systemd/system
cp px5server.service tmp/etc/systemd/system/px5server.service

# Udev rules
mkdir -p tmp/etc/udev/rules.d
cp 10-usb.rules tmp/etc/udev/rules.d/10-usb.rules

# Build package
fpm -s dir -C tmp -t deb -a all --name px5server \
    --version 0.1.0 --depends python3 --iteration 1 \
    --description "USB<->TCP bridge for amptek px5 ethernet."  .

# Note:
# The server requires python3-usb but there is no deb.
# The library has to be installed using:
# $ sudo pip3 install usb
