#!/usr/bin/env python3
import sys
import time

from common import Device
from logger import log
from functions import UserInputThread, check_modemmanager

import usb.core
import usb.util

import struct
import os

def p32(x):
    return struct.pack(">I", x)
    
def raise_(ex):
    raise ex


def to_bytes(value, size=1, endian='>'):
    return {
        1: lambda: struct.pack(endian + 'B', value),
        2: lambda: struct.pack(endian + 'H', value),
        4: lambda: struct.pack(endian + 'I', value)
    }.get(size, lambda: raise_(RuntimeError("invalid size")))()


def from_bytes(value, size=1, endian='>'):
    return {
        1: lambda: struct.unpack(endian + 'B', value)[0],
        2: lambda: struct.unpack(endian + 'H', value)[0],
        4: lambda: struct.unpack(endian + 'I', value)[0]
    }.get(size, lambda: raise_(RuntimeError("invalid size")))()

def load_payload_file(path):
    with open(path, "rb") as fin:
        payload = fin.read()
    log("Load payload from {} = 0x{:X} bytes".format(path, len(payload)))
    while len(payload) % 4 != 0:
        payload += b"\x00"

    return payload

def attempt2(d):

    payload = load_payload_file("../brom-payload/stage1/stage1.bin")
    payload += b'\x00' * 0x100
    
    size = len(payload)
    
    #send DA
    
    d.write(b"\xD7")
    result = d.read(1)
    d.write(p32(0x200D00))
    result = d.read(4)
    d.write(p32(size))
    result = d.read(4)
    d.write(p32(0x100))
    result = d.read(4)
    
    status = d.read(2)
    
    if from_bytes(status, 2) != 0:
        raise RuntimeError("status is {}".format(status.hex()))

    d.write(payload)
    
    checksum = d.read(2)
    status = d.read(2)
    
    if from_bytes(status, 2) != 0:
        raise RuntimeError("status is {}".format(status.hex()))
    
    # jump DA
    d.write(b"\xD5")
    result = d.read(1)
    d.write(p32(0x200D00))
    result = d.read(4)
    
    status = d.read(2)
    
    if from_bytes(status, 2) != 0:
        raise RuntimeError("status is {}".format(status.hex()))

def noop(*args, **kwargs):
    pass

def load_payload(dev):
    log("Handshake")
    dev.handshake()
    log("Disable watchdog")
    dev.write32(0x10007000, 0x22000000)

    thread = UserInputThread()
    thread.start()
    while not thread.done:
        dev.write32(0x10007008, 0x1971) # low-level watchdog kick
        time.sleep(1)

    d = dev.dev

    addr = 0x10007050
    result = dev.read32(addr)
    dev.write32(addr, [0xA1000]) # 00 10 0A 00
    result = dev.read32(addr)

    readl = 0x24
    result = dev.read32(addr - 0x20, readl//4)

    dev.write32(addr, 0)

    attempt2(d)

    #udev = usb.core.find(idVendor=0x0E8D, idProduct=0x3)
    
    #try:
        # noinspection PyProtectedMember
        #udev._ctx.managed_claim_interface = lambda *args, **kwargs: None
    #except AttributeError as e:
        #raise RuntimeError("libusb is not installed for port {}".format(device.dev.port)) from e

    log("Let's rock")
    #try:
        #udev.ctrl_transfer(0xA1, 0, 0, 10, 0)
    #except usb.core.USBError as e:
        #print(e)

    # clear 2 more bytes
    #d.read(2)

    log("Waiting for stage 1 to come online...")

    data = d.read(4)
    log(data)
    
    if data != to_bytes(0xA1A2A3A4, 4):
        raise RuntimeError("received {} instead of expected pattern".format(data))

    dev.kick_watchdog()

    log("All good")

    log("Load 2nd stage payload")
    stage2=load_payload_file("../brom-payload/stage2/stage2.bin")

    log("Send 2nd stage payload")
    # magic
    d.write(p32(0xf00dd00d))
    # cmd
    d.write(p32(0x4000))
    # address to write
    d.write(p32(0x201000))
    # length
    d.write(p32(len(stage2)))
    # data
    d.write(stage2)

    code = d.read(4)
    if code != b"\xd0\xd0\xd0\xd0":
        raise RuntimeError("device failure")

    dev.kick_watchdog()

    log("Party time")
    # magic
    d.write(p32(0xf00dd00d))
    # cmd
    d.write(p32(0x4001))
    # address to write
    d.write(p32(0x201000))

    log("Waiting for stage 2 to come online...")

    data = d.read(4)
    if data != b"\xB1\xB2\xB3\xB4":
        raise RuntimeError("received {} instead of expected pattern".format(data))

    log("All good")

    dev.kick_watchdog()

if __name__ == "__main__":

    check_modemmanager()

    if len(sys.argv) > 1:
        dev = Device(sys.argv[1])
    else:
        dev = Device()
        dev.find_device()

    load_payload(dev)
