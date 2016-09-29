#!/bin/bash
# Dirty script to create rpi deb for px5server
cd `dirname $0`
mkdir -p tmp/usr/bin
cp px5server.py tmp/usr/bin/px5server
chmod +x tmp/usr/bin/px5server

mkdir -p tmp/etc/systemd/system
cp px5server.service tmp/etc/systemd/system/px5server.service


# requires python3-usb but there is no deb, install using pip
fpm -s dir -C tmp -t deb -a all --name px5server --version 0.0.1 --depends python3 --iteration 1 --description "USB<->TCP bridge for amptek px5 ethernet."  .
