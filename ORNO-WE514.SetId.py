#!/usr/bin/env python3

# Use with ORNO WE514 RS485 power meters
#
# Change WE514 device ID 
# Thanks to PeWu (https://github.com/PeWu/orno_modbus) for the write enabling procedure
# Have a look at the ORNO Register List OR-WE-514_MODBUS_Registers_List.pdf
# from the Orno Support page (https://orno.pl/en/download-old-product-manuals)

# Copyright 2022 Federico Scaramuzza
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
#import pymodbus
#import serial
import sys
import time

from pymodbus.constants import Defaults as ModbusDefaults
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.pdu import ModbusRequest

# Function 0x28 is not a Standard Function Code according to ModBus specs
# It is even outside the range dedicated to Custom Function Code and its 
# syntax is undocumented.
# Default password is 00000000 (four zeroed bytes)
class SendOrnoPassword(ModbusRequest):
    function_code = 0x28
    _rtu_frame_size = 13

    def __init__(self, **kwargs):
        ModbusRequest.__init__(self, **kwargs)

    def encode(self):
        # This byte sequence works only to write the ID register
        # It fails to enable writing to other registers
        writeEnableCmd = b'\xfe\x01\x00\x02\x04\x00\x00\x00\x00'
        return writeEnableCmd


def readID(id):
    registerAddress = 0x110
    result = -1
    try:
        rr = client.read_holding_registers(address=registerAddress, count=1, unit=id)
        if id == rr.registers[0]:
            result = 0
        else:
            result = -1
    except Exception as ex:
        result = -1
        print("Error reading ID from unit %d." % id )
    finally:
        return result


# Main begins here
# ----------------
FORMAT = ('%(asctime)-15s %(threadName)-15s'
          ' %(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
# Comment out WARN to read transmitted bytes
log.setLevel(logging.DEBUG)
log.setLevel(logging.WARN)

if len(sys.argv) != 3:
    print(
"""Usage:
    %s current_address new_address """ % sys.argv[0],
"""
Example: to change from ID 1 to ID 2
    %s 1 2 """ % sys.argv[0],
"""
Use 0 as current address to broadcast the command.
""")
    sys.exit(0)

currentID = int(sys.argv[1])
desiredID = int(sys.argv[2])

client = ModbusClient(method='rtu', port='/dev/ttyUSB0', timeout=1, stopbits=1, bytesize=8, parity='E', baudrate=9600)
client.connect()

# Read current ID
if readID(currentID) != 0:
    print("Something went wrong with ID %d. Exiting." % currentID )
    sys.exit(1)
else:
    print("Current ID is %d." % currentID )

# Wait for confirmation
userKey = input("Proceed (yY/Nn)? ")
if userKey.lower() != "y":
    sys.exit(0) 

# Send a request to enable a 10-second write window.
writeRequest = SendOrnoPassword(unit=currentID)
client.execute(writeRequest)

# Write new ID
try:
    # Single Register Write does not work...
    # Response frame 0x86 0x01 means "Single Write Error: function not supported"
    # client.write_register(address=0x110, value=desiredID, unit=currentID)
    client.write_registers(0x110, [desiredID], unit=currentID)
    # Unwanted response frame 0x90 0x04 means "Multiple Write Error: Write failed"
except Exception as ex:
    print("Error changing to ID %d. Exiting" % desiredID )
    sys.exit(1)

userKey = input("Write done. Read again (yY/Nn)? ")
if userKey.lower() != "y":
    sys.exit(0)
# Read ID
if readID(desiredID) == 0:
    print("Unit has now ID %d." % desiredID )
    
 

# EOF
