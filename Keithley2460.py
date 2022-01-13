#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 14 14:39:56 2020

Device server to use a Keithley 2460 SourceMeter to drive an electromagnet.
Configures the hardware device to source current and maintains a history of
current setpoints.

@author: Michael Schneider <mschneid@mbi-berlin.de>, Max Born Institut Berlin
"""


import pyvisa as visa

import tango
from tango import DevState
from tango.server import Device, attribute, command
from tango.server import device_property
from tango import READ, READ_WRITE
import sys

import numpy as np


class Keithley2460(Device):
    
    current = attribute(
            name='current',
            access=READ_WRITE,
            unit='A',
            dtype=tango.DevFloat,
            format='%.3f',
            )

    voltage = attribute(
            name='voltage',
            access=READ,
            unit='V',
            dtype=tango.DevFloat,
            format='%.3f',
            )

    curr_hist = attribute(
            name='curr_hist',
            access=READ,
            dtype=(float,),
            max_dim_x=100000,
            )
    
    output = attribute(
            name='output',
            access=READ_WRITE,
            dtype=tango.DevBoolean,
            )
    
    setpoint_reached = attribute(
            name='setpoint_reached',
            access=READ,
            dtype=tango.DevBoolean,
            )
    
    host = device_property(
            dtype=str,
            mandatory=True,
            update_db=True,
            )
    
    def init_device(self):
        Device.init_device(self)
        self.rm = visa.ResourceManager('@py')
        self.inst = self.rm.open_resource(f'TCPIP::{self.host}::INSTR')
        try:
            self.inst.write('*RST')
            ans = self.inst.query('*IDN?')
            print(ans)
            if 'MODEL 2460' in ans:
                self.source_setup()
                self.set_state(DevState.ON)
            else:
                self.set_state(DevState.FAULT)
                sys.exit(255)
        except Exception as e:
            print(e, file=self.error_stream)
            self.inst.close()
            self.set_state(DevState.FAULT)
            sys.exit(255)
        self._setpoint = self.read_current()
        self._history = [self._setpoint]
        self.write_output(True)
    
    def read_current(self):
        ans = self.inst.query(':SOUR:CURR?')
        print('current read', ans, file=self.log_debug)
        return float(ans)
    
    def read_curr_hist(self):
        return self._history

    def read_setpoint_reached(self):
        in_pos = np.allclose(self.read_current(), self._setpoint,
                             rtol=1e-2, atol=1e-2)
        if in_pos:
            self.set_state(DevState.ON)
        return in_pos
    
    def write_current(self, value):
        if float(value) == 0:
            value = 1e-7
        self.inst.write(f'SOUR:CURR {value:.8f}')
        self._setpoint = value
        self._history.append(value)
        self.set_state(DevState.MOVING)

    @command
    def clear_history(self):
        self._history = [self._history[-1],]
    
    def source_setup(self):
        self.inst.write('ROUT:TERM FRON')  # use front terminal out
        self.inst.write('SENS:FUNC "VOLT"')
        self.inst.write('SENS:CURR:NPLC 1')
        self.inst.write('SENS:CURR:RANG:AUTO ON')
        self.inst.write('SOUR:FUNC CURR')
        self.inst.write('SOUR:CURR:READ:BACK 1')
        self.inst.write('SOUR:CURR:VLIM 100')
            
    @command
    def reset_device(self):
        self.inst.write('*RST')
        self.source_setup()
        self.write_output(True)
        
    def read_voltage(self):
        ans = self.inst.query(':READ?')
        return float(ans)
        
    def read_output(self):
        ans = self.inst.query('OUTP?').strip()
        return True if ans == '1' else False
    
    def write_output(self, value):
        val = 'ON' if value else 'OFF'
        self.inst.write('OUTP ' + val)
           

if __name__ == "__main__":
    Keithley2460.run_server()
